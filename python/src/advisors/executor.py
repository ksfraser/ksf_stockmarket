"""Shared advisor execution engine.

Provides a reusable portfolio simulation that can write either to
backtest tables or to live transactions/portfolio tables.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Position:
    symbol: str
    shares: int
    cost_basis: float
    entry_date: date
    strategy: str
    trigger_reason: str = ""


@dataclass
class Trade:
    symbol: str
    trade_type: str
    trade_date: date
    price: float
    quantity: int
    commission: float
    total_cost: float
    pnl: float = 0.0
    signal_reasons: str = ""


@dataclass
class PortfolioSnapshot:
    current_date: date
    cash: float
    positions: dict[str, Position]
    total_value: float = 0.0


class AdvisorExecutor:
    """Reusable advisor execution engine.

    Runs a strategy over historical dates, simulates BUY/SELL,
    and yields trades/snapshots. Persistence is delegated to a
    separate persister so this class stays framework-agnostic.
    """

    commission: float = 9.99
    max_position_pct: float = 0.01

    def __init__(self, strategy: Any, config: dict[str, Any] | None = None) -> None:
        self.strategy = strategy
        self.config = config or {}
        self.frequency = self.config.get("schedule", "daily")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _rebalance_days(self) -> int:
        return {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 91}.get(
            self.frequency, 7
        )

    def _get_price(self, db: Any, symbol: str, target_date: date) -> float | None:
        with db.cursor() as cur:
            cur.execute(
                "SELECT close FROM stockprices WHERE symbol = %s AND price_date <= %s ORDER BY price_date DESC LIMIT 1",
                (symbol, target_date),
            )
            row = cur.fetchone()
            return float(row["close"]) if row else None

    def _snapshot(self, db: Any, current_date: date, cash: float,
                  positions: dict[str, Position]) -> PortfolioSnapshot:
        equity = cash
        for pos in positions.values():
            price = self._get_price(db, pos.symbol, current_date) or 0.0
            equity += pos.shares * price
        return PortfolioSnapshot(
            current_date=current_date,
            cash=cash,
            positions=dict(positions),
            total_value=equity,
        )

    # ------------------------------------------------------------------
    # Core simulation
    # ------------------------------------------------------------------
    def run(
        self,
        db: Any,
        user_id: int,
        start_date: date,
        end_date: date,
        initial_capital: float = 100_000.0,
        max_positions: int = 20,
    ) -> dict[str, Any]:
        cash = float(initial_capital)
        positions: dict[str, Position] = {}
        trades: list[Trade] = []
        history: list[PortfolioSnapshot] = []

        dates = self._trading_dates(db, start_date, end_date)
        if not dates:
            return {"error": "No trading data"}

        rebalance_days = self._rebalance_days()
        last_rebalance = start_date - __import__("datetime").timedelta(days=30)
        max_positions = int(max_positions)

        # Fast-exit if universe empty at start
        try:
            universe = self.strategy.select_universe(start_date)
        except Exception as exc:
            return {"error": f"Universe error: {exc}"}

        if not universe:
            return {"error": "Empty universe at start date"}

        cap = min(len(universe), max_positions * 2)
        if cap < len(universe):
            logger.info("Truncating universe from %d to %d", len(universe), cap)
            universe = universe[:cap]

        for i, current_date in enumerate(dates):
            if (current_date - last_rebalance).days < rebalance_days:
                if i % 5 == 0:
                    history.append(self._snapshot(db, current_date, cash, positions))
                continue

            last_rebalance = current_date
            try:
                signals = self.strategy.generate_signals(
                    current_date, max_positions=max_positions
                )
            except Exception as exc:
                logger.warning("Strategy failed on %s: %s", current_date, exc)
                history.append(self._snapshot(db, current_date, cash, positions))
                continue

            if not signals:
                history.append(self._snapshot(db, current_date, cash, positions))
                continue

            sells = [s for s in signals if s.action == "SELL"]
            buys = [s for s in signals if s.action == "BUY"]

            target_symbols = {s.symbol for s in buys}

            # Auto-sell positions dropped from target list (Buffett-style rebalance)
            for sym in list(positions.keys()):
                if sym in target_symbols:
                    continue
                pos = positions[sym]
                price = self._get_price(db, sym, current_date)
                if not price or price <= 0:
                    continue
                qty = pos.shares
                proceeds = qty * price - self.commission
                pnl = proceeds - (qty * pos.cost_basis)
                cash += proceeds
                trades.append(Trade(
                    symbol=sym,
                    trade_type="SELL",
                    trade_date=current_date,
                    price=price,
                    quantity=qty,
                    commission=self.commission,
                    total_cost=-proceeds,
                    pnl=pnl,
                    signal_reasons="rebalance_out",
                ))
                del positions[sym]

            for sig in sells:
                if sig.symbol not in positions:
                    continue
                price = self._get_price(db, sig.symbol, current_date)
                if not price or price <= 0:
                    continue
                pos = positions[sig.symbol]
                qty = pos.shares
                proceeds = qty * price - self.commission
                pnl = proceeds - (qty * pos.cost_basis)
                cash += proceeds
                trades.append(Trade(
                    symbol=sig.symbol,
                    trade_type="SELL",
                    trade_date=current_date,
                    price=price,
                    quantity=qty,
                    commission=self.commission,
                    total_cost=-proceeds,
                    pnl=pnl,
                    signal_reasons=sig.reason,
                ))
                del positions[sig.symbol]

            target_weight = 1.0 / max(max_positions, 1)
            for sig in buys:
                if sig.symbol in positions:
                    continue
                if len(positions) >= max_positions:
                    break

                price = self._get_price(db, sig.symbol, current_date)
                if not price or price <= 0:
                    continue

                allocation = cash * target_weight
                shares = int(allocation / price)
                if shares <= 0:
                    continue
                cost = shares * price + self.commission
                if cost > cash:
                    shares = int((cash - self.commission) / price)
                    if shares <= 0:
                        continue
                    cost = shares * price + self.commission

                cash -= cost
                positions[sig.symbol] = Position(
                    symbol=sig.symbol,
                    shares=shares,
                    cost_basis=price,
                    entry_date=current_date,
                    strategy=self.strategy.slug,
                    trigger_reason=sig.reason,
                )
                trades.append(Trade(
                    symbol=sig.symbol,
                    trade_type="BUY",
                    trade_date=current_date,
                    price=price,
                    quantity=shares,
                    commission=self.commission,
                    total_cost=cost,
                    signal_reasons=sig.reason,
                ))

            history.append(self._snapshot(db, current_date, cash, positions))

        final_snap = self._snapshot(db, dates[-1], cash, positions)
        history.append(final_snap)
        final_value = final_snap.total_value
        total_return = (final_value - initial_capital) / initial_capital if initial_capital else 0.0
        years = (end_date - start_date).days / 365.25
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

        peak = initial_capital
        max_drawdown = 0.0
        for snap in history:
            if snap.total_value > peak:
                peak = snap.total_value
            dd = (peak - snap.total_value) / peak if peak > 0 else 0.0
            if dd > max_drawdown:
                max_drawdown = dd

        winning = [t for t in trades if t.pnl > 0]
        win_rate = len(winning) / len(trades) if trades else 0.0

        return {
            "trades": [self._trade_to_dict(t) for t in trades],
            "history": [self._snapshot_to_dict(s) for s in history],
            "summary": {
                "initial_capital": initial_capital,
                "final_value": round(final_value, 2),
                "total_return_pct": round(total_return * 100, 2),
                "annualized_return_pct": round(annualized_return * 100, 2),
                "max_drawdown_pct": round(max_drawdown * 100, 2),
                "num_trades": len(trades),
                "win_rate_pct": round(win_rate * 100, 2),
            },
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    @staticmethod
    def _trade_to_dict(t: Trade) -> dict[str, Any]:
        return {
            "symbol": t.symbol,
            "trade_type": t.trade_type,
            "trade_date": t.trade_date.isoformat(),
            "price": t.price,
            "quantity": t.quantity,
            "commission": t.commission,
            "total_cost": t.total_cost,
            "pnl": t.pnl,
            "signal_reasons": t.signal_reasons,
        }

    @staticmethod
    def _snapshot_to_dict(s: PortfolioSnapshot) -> dict[str, Any]:
        return {
            "current_date": s.current_date.isoformat(),
            "cash": s.cash,
            "positions": {sym: {
                "symbol": p.symbol,
                "shares": p.shares,
                "cost_basis": p.cost_basis,
                "entry_date": p.entry_date.isoformat(),
                "strategy": p.strategy,
            } for sym, p in s.positions.items()},
            "total_value": s.total_value,
        }

    def _trading_dates(self, db: Any, start: date, end: date) -> list[date]:
        with db.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT price_date FROM stockprices WHERE price_date BETWEEN %s AND %s ORDER BY price_date ASC",
                (start, end),
            )
            return [row["price_date"] for row in cur.fetchall()]

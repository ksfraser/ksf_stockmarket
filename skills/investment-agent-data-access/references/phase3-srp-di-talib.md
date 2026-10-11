# Phase 3 — SRP / DI / TA-Lib extraction recipe (indicator & analyzer monster)

Concrete layout used to extract `src/indicators/investment_monitor.py` (~2060 lines)
into single-responsibility classes without breaking the live Hermes crons.

## Golden rules
1. **SRP classes + DI ports = guard-clean, NO `yfinance`.** They live in
   `src/indicators/` and only accept data (DataFrames / dicts). The guard blocks
   `yf` in `src/indicators/`, so any edit to the monster there forces the whole
   file yf-free in that commit — which is why you extract into NEW files first.
2. **Concrete yf impls need an allowlisted home.** The DI ports are interfaces; the
   real fetcher must wrap `YFinanceFetcher` (in `src/db/price_fetcher.py`, which IS
   in `ALLOW_YF`) or live in a module you add to `ALLOW_YF`. Do NOT put raw
   `yf.Ticker` in `src/common/market_data.py` — it is the façade and is NOT in
   `ALLOW_YF`; have it delegate to `YFinanceFetcher`.
3. **Keep the legacy output KEY SET.** Downstream code reads the monster's output
   dict by key. The SRP service must emit the same keys (TechnicalAnalyzer = 40 keys)
   so the rewire is a drop-in.
4. **TA-Lib is canonical.** TA-Lib 0.7.0 is installed. Indicators ⇒ thin TA-Lib
   wrappers; pandas only for price-change / realized-vol / support-resistance.

## DI port layout (`src/indicators/market_data_port.py`)
```python
@runtime_checkable
class MarketDataPort(Protocol):
    def get_price_history(self, symbol, period="6mo", interval="1d") -> pd.DataFrame: ...

@runtime_checkable
class FundamentalsPort(Protocol):
    def get_fundamentals(self, symbol) -> Dict: ...

@runtime_checkable
class NewsPort(Protocol):
    def get_news(self, symbol) -> Dict: ...

@runtime_checkable
class SectorDataPort(Protocol):
    def fetch_sector_inputs(self, sector) -> Dict: ...   # etf hist/info + peers

@runtime_checkable
class IndexDataPort(Protocol):
    def get_vix(self) -> float: ...
    def get_index_history(self, symbol, period="6mo") -> pd.DataFrame: ...
```
Plus no-network stubs (`StubMarketData`, `StubFundamentals`, `StubNews`,
`StubSectorData`) that return canned DataFrames/dicts — these let every test run
without the network and prove the DI seam works (`analyzer.analyze(stub_inputs)`).

## TA-Lib wrapper convention (`src/indicators/technical_indicators.py`)
Each calculator: `calculate(df) -> Dict`, composed by `TechnicalAnalysisService`
(calculators injectable). Example:
```python
class RSIIndicator:
    name = "rsi"
    def calculate(self, df):
        rsi = talib.RSI(df["Close"], timeperiod=14)
        return {"rsi": _last(rsi), "rsi_divergence": _divergence(df["Close"], rsi)}

class TechnicalAnalysisService:
    def __init__(self, calculators=None):
        self.calculators = calculators or list(DEFAULT_CALCULATORS)
    def analyze(self, df):
        out = {}
        for c in self.calculators:
            out.update(c.calculate(df))
        return out
```
DRY shared helpers (`_sma`, `_last`, `_trend_duration`, `_consecutive`,
`_pct_change`, `_divergence`, `_crossover_days_ago`) live at module level.

## Structural-parity test (the key guard against silent rewire breakage)
```python
def test_structural_parity_with_monster(ohlcv):
    from investment_monitor import TechnicalAnalyzer
    monster = TechnicalAnalyzer.calculate(ohlcv)
    srp = TechnicalAnalysisService().calculate(ohlcv)
    assert set(monster.keys()) == set(srp.keys())   # NOT value equality
    assert len(srp) == 40
```
Values intentionally DIVERGE under TA-Lib (Wilder RSI, EMA-based MACD) — that is
the upgrade. Assert only the key contract. Flag to Kevin that live signal values
will shift when the monster is flipped onto the service.

## Analyzer SRPs (`src/indicators/analysis_srps.py`) — pure logic, injected data
`FundamentalScorer`, `SectorPerformanceAnalyzer`, `BacktestRunner` (injectable
`indicator_fn`/`signal_fn`), `MacroRegimeAnalyzer`, `MarketRelativeAnalyzer`,
`VolumeProfileAnalyzer`, `NewsProcessor`. None import yf or touch I/O; each keeps
the monster's exact output key names.

## Test suite shape (pytest)
- per-SRP unit tests (ranges, not legacy-exact values)
- DI-substitution test (fake calculator ⇒ service returns only the fake's output)
- monster characterization test (structural parity + monster still runs)
- analyzer + DI-port/stub suites

Run: `python3 -m pytest` (pytest.ini sets `pythonpath = src src/indicators`).

## Sequence to a full rewire
1. SRP classes + DI ports + stubs + tests in `src/indicators/` (guard-clean). ✅ done
2. Concrete fetchers wrapping `YFinanceFetcher` in the allowlisted data layer
   (+ extend `ALLOW_YF` if a new module is introduced). ← next
3. Consolidated `investment_monitor.py` rewire: replace its `yf` calls with injected
   ports, removing all `yf` from the file in ONE guarded commit. ← final

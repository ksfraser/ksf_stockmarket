"""Evaluation domain DTOs.

Each DTO maps exactly to its production table columns on ksfraser_stock_market.
Notable schema facts:
  - motleyfool: motleyfool_criteria BOOL columns + score + lastupdate
  - tenets: one row per (symbol, name) with passed BOOL + detail
  - evalbusiness / evalmanagement / evalmarket: symbol + score + summary + lasteval
  - evaluation_scores: symbolic scores with eval_type / domain / grade / note
  - evalsummary: symbol + price_date + close + strategy_json (no source columns)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass
class MotleyFoolEval:
    symbol: str
    simple_business: Optional[bool] = None
    reasonable_valuation: Optional[bool] = None
    core_focus: Optional[bool] = None
    doubledigit_sales: Optional[bool] = None
    rising_cashflow: Optional[bool] = None
    rising_bookvalue: Optional[bool] = None
    improving_margins: Optional[bool] = None
    rising_roe: Optional[bool] = None
    insider_ownership: Optional[bool] = None
    regular_dividend: Optional[bool] = None
    score: int = 0
    lastupdate: Optional[date] = None


@dataclass
class TenetRow:
    symbol: str
    name: str
    passed: bool = False
    detail: str = ""
    lasteval: Optional[datetime] = None


@dataclass
class EvaluationRow:
    symbol: str
    eval_type: str
    domain: str
    score: int = 0
    max_score: int = 100
    grade: str = "F"
    note: Optional[str] = None
    created_by: str = "system"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class BusinessQualityEval:
    symbol: str
    score: int = 0
    summary: str = ""
    lasteval: Optional[datetime] = None


@dataclass
class ManagementEvaluation:
    symbol: str
    score: int = 0
    summary: str = ""
    lasteval: Optional[datetime] = None


@dataclass
class MarketEvaluation:
    symbol: str
    score: int = 0
    summary: str = ""
    lasteval: Optional[datetime] = None


@dataclass
class EvalSummary:
    symbol: str
    price_date: Optional[date] = None
    close: Optional[float] = None
    consensus_signal: Optional[int] = None
    consensus_strength: Optional[float] = None
    atr_position_size: Optional[float] = None
    portfolio_weight: Optional[float] = None
    strategy_json: Optional[str] = None

"""
wealthsystem_port.py — Ported WealthSystem scoring thresholds + methodology logic
==================================================================================
Ports the following from WealthSystem/Stock-Analysis-Extension:
- Warren Buffett 12-tenet scoring and recommendation thresholds
- Motley Fool 10-criterion scoring and recommendation thresholds  
- Evaluation Analyzer (business/financial/management/market) weighted scores
- IPlace composite scoring weights and criteria
- Technical Analysis signal weights
- Unified consensus methodology

Weights/thresholds sourced from:
  /home/kevin/Documents/WealthSystem/Stock-Analysis-Extension/Legacy/src/Ksfraser/

This module is used by the strategy pipeline and advisor framework to:
  1. Generate per-symbol analysis scores
  2. Produce consensus recommendations for hired advisors
  3. Feed the in-detail research pages (Buffett, MF, TA, Evaluations, LLM)

All weights are configurable via JSON/YAML if you want to experiment.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# BUFFETT 12 TENETS — ported from BuffettAnalyzer.php
# ============================================================================

BUFFETT_TENETS: List[Dict[str, Any]] = [
    {"id": "simple",              "label": "Simple Business",            "max": 1},
    {"id": "consistent",          "label": "Consistent Performance",     "max": 1},
    {"id": "longterm",            "label": "Long-Term Prospects",        "max": 1},
    {"id": "rationalmanager",     "label": "Rational Management",        "max": 1},
    {"id": "candid",              "label": "Candid with Shareholders",   "max": 1},
    {"id": "resistinstitution",   "label": "Resists Institutional Pressure", "max": 1},
    {"id": "focusroe",            "label": "Focus on ROE, not EPS",      "max": 1},
    {"id": "ownerearnings",       "label": "Positive Owner Earnings",    "max": 1},
    {"id": "highprofitmargin",    "label": "High Profit Margins",        "max": 1},
    {"id": "retainedtomarket",    "label": "Retained Earnings → Market Value", "max": 1},
    {"id": "valueofbusiness",     "label": "Understandable Value",       "max": 1},
    {"id": "discounted",          "label": "Buy at Discount to Value",   "max": 1},
]

# Recommendation thresholds from getBuffettRecommendationText() / getBuffettRiskLevel()
BUFFETT_RECOMMENDATION_THRESHOLDS = [
    {"min_tenets": 10, "min_margin_safety_pct": 25, "rec": "Strong Buy",
     "risk": "Very Low"},
    {"min_tenets": 8,  "min_margin_safety_pct": 15, "rec": "Buy",
     "risk": "Low"},
    {"min_tenets": 6,  "min_margin_safety_pct": 0,  "rec": "Hold",
     "risk": "Medium"},
    {"min_tenets": 4,  "min_margin_safety_pct": 0,  "rec": "Caution",
     "risk": "High"},
    {"min_tenets": 0,  "min_margin_safety_pct": 0,  "rec": "Avoid",
     "risk": "Very High"},
]

BUFFETT_MAX_TENETS = 12


def buffett_recommendation(tenets_score: int, margin_of_safety_pct: float) -> Tuple[str, str]:
    """Return (recommendation, risk_level) based on WealthSystem thresholds."""
    for tier in BUFFETT_RECOMMENDATION_THRESHOLDS:
        if tenets_score >= tier["min_tenets"] and margin_of_safety_pct >= tier["min_margin_safety_pct"]:
            return tier["rec"], tier["risk"]
    return "Avoid", "Very High"


def buffett_tenets_percentage(tenets_score: int) -> float:
    return round((tenets_score / BUFFETT_MAX_TENETS) * 100, 1)


# ============================================================================
# MOTLEY FOOL 10 CRITERIA — ported from MotleyFoolAnalyzer.php
# ============================================================================

MF_CRITERIA: List[Dict[str, Any]] = [
    {"id": "simplebusiness",       "label": "Simple Business",       "max": 1},
    {"id": "reasonablevaluation",  "label": "Reasonable Valuation",  "max": 1},
    {"id": "corefocus",            "label": "Core Focus",            "max": 1},
    {"id": "doubledigitsales",     "label": "Double-Digit Sales Growth", "max": 1},
    {"id": "risingcashflow",       "label": "Rising Cash Flow",      "max": 1},
    {"id": "risingbookvalue",      "label": "Rising Book Value",     "max": 1},
    {"id": "improvingmargins",     "label": "Improving Margins",     "max": 1},
    {"id": "risingroe",            "label": "Rising ROE",            "max": 1},
    {"id": "insiderownership",     "label": "Insider Ownership",     "max": 1},
    {"id": "regulardividend",      "label": "Regular Dividend",      "max": 1},
]

# Recommendation thresholds from getRecommendationText() / getRiskLevel()
MF_RECOMMENDATION_THRESHOLDS = [
    {"min_score": 9, "rec": "Strong Buy", "risk": "Low"},
    {"min_score": 7, "rec": "Buy",        "risk": "Low"},
    {"min_score": 5, "rec": "Hold",       "risk": "Medium"},
    {"min_score": 3, "rec": "Caution",    "risk": "High"},
    {"min_score": 0, "rec": "Avoid",      "risk": "Very High"},
]

MF_MAX_CRITERIA = 10


def mf_recommendation(score: int) -> Tuple[str, str]:
    for tier in MF_RECOMMENDATION_THRESHOLDS:
        if score >= tier["min_score"]:
            return tier["rec"], tier["risk"]
    return "Avoid", "Very High"


def mf_percentage(score: int) -> float:
    return round((score / MF_MAX_CRITERIA) * 100, 1)


# ============================================================================
# EVALUATION ANALYZER — ported from EvaluationAnalyzer.php
# ============================================================================

# Weights from calculateOverallScore()
EVAL_WEIGHTS = {
    "business":   0.25,
    "financial":  0.30,
    "management": 0.25,
    "market":     0.20,
}

# Recommendation thresholds from getOverallRecommendation()
EVAL_RECOMMENDATION_THRESHOLDS = [
    {"min_score": 85, "rec": "Strong Buy"},
    {"min_score": 75, "rec": "Buy"},
    {"min_score": 65, "rec": "Moderate Buy"},
    {"min_score": 55, "rec": "Hold"},
    {"min_score": 45, "rec": "Weak Hold"},
    {"min_score": 35, "rec": "Sell"},
    {"min_score": 0,  "rec": "Strong Sell"},
]


def eval_recommendation(overall_score: float) -> str:
    for tier in EVAL_RECOMMENDATION_THRESHOLDS:
        if overall_score >= tier["min_score"]:
            return tier["rec"]
    return "Strong Sell"


def eval_grade(score: float) -> str:
    if score >= 95: return "A+"
    if score >= 90: return "A"
    if score >= 85: return "A-"
    if score >= 80: return "B+"
    if score >= 75: return "B"
    if score >= 70: return "B-"
    if score >= 65: return "C+"
    if score >= 60: return "C"
    if score >= 55: return "C-"
    if score >= 50: return "D+"
    if score >= 45: return "D"
    return "F"


def eval_overall_score(scores: Dict[str, float]) -> float:
    """Weighted overall score from individual domain scores."""
    total = 0.0
    weight_sum = 0.0
    for domain, weight in EVAL_WEIGHTS.items():
        val = scores.get(domain)
        if val is not None:
            total += val * weight
            weight_sum += weight
    return round(total / weight_sum, 1) if weight_sum > 0 else 0.0


# ============================================================================
# IPLACE (InvestorPlace) — ported from IPlaceAnalyzer.php
# ============================================================================

IPLACE_CRITERIA = [
    {"id": "seventyfivepercent",   "label": "75% Domestic Sales",       "max": 1},
    {"id": "earningsgrowth",       "label": "Earnings Growing",         "max": 1},
    {"id": "earningsaccel",        "label": "Earnings Accelerating",    "max": 1},
    {"id": "pe",                   "label": "Reasonable PE",            "max": 1},
    {"id": "tradingvolume",        "label": "Strong Volume",            "max": 1},
    {"id": "institutioninterest",  "label": "Institutional Interest",   "max": 1},
    {"id": "orderimbalance",       "label": "Buy Order Imbalance",      "max": 1},
    {"id": "shortinterest",        "label": "Low Short Interest",       "max": 1},
    {"id": "volatility",           "label": "Controlled Volatility",    "max": 1},
    {"id": "dividendearningratio", "label": "Dividend/Earnings",        "max": 1},
    {"id": "newproductline",       "label": "New Products/Services",    "max": 1},
    {"id": "restructuring",        "label": "Restructuring for Value",  "max": 1},
    {"id": "reengineering",        "label": "Reengineering",            "max": 1},
    {"id": "sharebuyback",         "label": "Share Buyback",            "max": 1},
    {"id": "headcountcuts",        "label": "Efficiency Gains",         "max": 1},
    {"id": "spinoffs",             "label": "Focused via Spinoffs",     "max": 1},
    {"id": "reducedrd",            "label": "R&D Discipline",           "max": 1},
    {"id": "extracash",            "label": "Excess Cash",              "max": 1},
    {"id": "shareholderprofitgoal","label": "Shareholder Profit Focus", "max": 1},
    {"id": "dividendincreases",    "label": "Dividend Growth Track Record", "max": 1},
]

IPLACE_MAX_CRITERIA = len(IPLACE_CRITERIA)


def iplace_composite_score(criteria: Dict[str, int]) -> float:
    """Simple percentage of criteria met."""
    if not criteria:
        return 0.0
    met = sum(1 for v in criteria.values() if v)
    return round((met / IPLACE_MAX_CRITERIA) * 100, 1)


# ============================================================================
# TECHNICAL ANALYSIS SIGNAL WEIGHTS — from TechnicalAnalysis.php
# ============================================================================

TA_SIGNAL_WEIGHTS = {
    "macd_bullish":        1,
    "golden_cross":        2,
    "sma_price_above_50":  1,
    "sma_price_above_200": 1,
    "death_cross":        -2,
    "macd_bearish":       -1,
}

TA_MAX_RAW_SCORE = sum(v for v in TA_SIGNAL_WEIGHTS.values() if v > 0)


def ta_signal_score(signals: Dict[str, bool]) -> float:
    """Score technical signals, normalized 0-100."""
    raw = 0
    for sig, weight in TA_SIGNAL_WEIGHTS.items():
        if signals.get(sig):
            raw += weight
    max_abs = max(TA_MAX_RAW_SCORE, 1)
    return round(((raw + max_abs) / (2 * max_abs)) * 100, 1)


# ============================================================================
# UNIFIED CONSENSUS — ported from UnifiedAnalyzer.php
# ============================================================================

def consensus_recommendation(
    buffett: Optional[Tuple[str, str]] = None,
    mf: Optional[Tuple[str, str]] = None,
    iplace: Optional[str] = None,
    evaluation: Optional[str] = None,
) -> Dict[str, Any]:
    """Weighted consensus from multiple methodologies."""
    recs: List[str] = []
    if buffett:       recs.append(buffett[0])
    if mf:            recs.append(mf[0])
    if iplace:        recs.append(iplace)
    if evaluation:    recs.append(evaluation)

    buy = sum(1 for r in recs if r in ("Strong Buy", "Buy", "Moderate Buy"))
    hold = sum(1 for r in recs if r in ("Hold", "Weak Hold"))
    sell = sum(1 for r in recs if r in ("Sell", "Strong Sell"))

    total = len(recs)
    if total == 0:
        return {"consensus": "INSUFFICIENT DATA", "confidence": 0.0,
                "distribution": {"buy": 0, "hold": 0, "sell": 0}}

    if buy > sell and buy > hold:
        consensus = "CONSENSUS BUY"
    elif sell > buy and sell > hold:
        consensus = "CONSENSUS SELL"
    elif hold >= buy and hold >= sell:
        consensus = "CONSENSUS HOLD"
    else:
        consensus = "MIXED SIGNALS"

    confidence = max(buy, hold, sell) / total

    return {
        "consensus": consensus,
        "confidence": round(confidence, 2),
        "distribution": {"buy": buy, "hold": hold, "sell": sell},
        "individual_recommendations": {
            "buffett": buffett[0] if buffett else None,
            "motley_fool": mf[0] if mf else None,
            "iplace": iplace,
            "evaluation": evaluation,
        },
    }


# ============================================================================
# LLM ANALYSIS PROMPT / PARSE UTILITIES
# ============================================================================

LLM_ANALYSIS_PROMPT = """
You are a sell-side equity research assistant. Analyze the following stock
and provide qualitative scores on a 1-5 scale (1=weak, 5=strong):

Symbol: {symbol}
Sector: {sector}
Current Price: {price}
Market Cap: {market_cap}
P/E: {pe_ratio}
EPS Growth (YoY): {earnings_growth}%
Revenue Growth (YoY): {revenue_growth}%
ROE: {roe}%

1. MANAGEMENT OPENNESS: Is management candid with shareholders?
   Rate 1-5 and give 2-3 sentences of evidence (earnings calls, filings, forecasts).

2. FORWARD GUIDANCE: How credible are management's forward projections?

3. COMPETITIVE MOAT: Is the competitive advantage durable? Rate 1-5.

4. KEY RISKS: List 3-5 specific risks to the bull case.

5. OPPORTUNITIES: List 2-3 specific growth vectors the market may be underpricing.

Respond in JSON with keys: management_openness (int 1-5), guidance_credibility (int 1-5),
moat_durability (int 1-5), openness_notes (string), risks (list[string]), opportunities (list[string]), thesis (string).
"""


def normalize_llm_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize LLM response into our schema."""
    return {
        "management_openness": int(raw.get("management_openness", 3)),
        "candor_score":        int(raw.get("guidance_credibility", 3)),
        "moat_durability":     int(raw.get("moat_durability", 3)),
        "risk_factors":        "; ".join(raw.get("risks", [])),
        "opportunities":       "; ".join(raw.get("opportunities", [])),
        "summary":             raw.get("thesis", ""),
        "raw_response":        raw,
    }


# ============================================================================
# DATA CLASSES FOR UI/PIPELINE
# ============================================================================

@dataclass
class BuffettAnalysis:
    symbol: str = ""
    tenets: Dict[str, int] = field(default_factory=dict)
    tenets_score: int = 0
    margin_of_safety_pct: float = 0.0
    recommendation: str = "Insufficient Data"
    risk_level: str = "Unknown"
    tenets_pct: float = 0.0
    evaluation: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "tenets": self.tenets,
            "tenets_score": self.tenets_score,
            "tenets_percentage": self.tenets_pct,
            "margin_of_safety_pct": self.margin_of_safety_pct,
            "recommendation": self.recommendation,
            "risk_level": self.risk_level,
            "evaluation": self.evaluation,
        }


@dataclass
class MFAnalysis:
    symbol: str = ""
    criteria: Dict[str, int] = field(default_factory=dict)
    score: int = 0
    score_pct: float = 0.0
    recommendation: str = "Insufficient Data"
    risk_level: str = "Unknown"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "criteria": self.criteria,
            "score": self.score,
            "score_percentage": self.score_pct,
            "recommendation": self.recommendation,
            "risk_level": self.risk_level,
        }


@dataclass
class EvalAnalysis:
    symbol: str = ""
    business_score: float = 0.0
    financial_score: float = 0.0
    management_score: float = 0.0
    market_score: float = 0.0
    overall_score: float = 0.0
    grade: str = "F"
    recommendation: str = "Insufficient Data"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "individual_scores": {
                "business": self.business_score,
                "financial": self.financial_score,
                "management": self.management_score,
                "market": self.market_score,
            },
            "overall_score": self.overall_score,
            "grade": self.grade,
            "recommendation": self.recommendation,
            "weights": EVAL_WEIGHTS,
        }


@dataclass
class LLMAnalysis:
    symbol: str = ""
    analysis_date: str = ""
    provider: str = ""
    model: str = ""
    management_openness: int = 0
    candor_score: int = 0
    moat_durability: int = 0
    risk_factors: str = ""
    opportunities: str = ""
    summary: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "analysis_date": self.analysis_date,
            "provider": self.provider,
            "model": self.model,
            "management_openness": self.management_openness,
            "candor_score": self.candor_score,
            "moat_durability": self.moat_durability,
            "risk_factors": self.risk_factors,
            "opportunities": self.opportunities,
            "summary": self.summary,
        }


@dataclass
class TAAnalysis:
    symbol: str = ""
    date: str = ""
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    rsi_14: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_middle: float = 0.0
    bollinger_lower: float = 0.0
    stochastic_k: float = 0.0
    stochastic_d: float = 0.0
    williams_r: float = 0.0
    atr: float = 0.0
    golden_cross: bool = False
    death_cross: bool = False
    signal_score: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "date": self.date,
            "sma_20": self.sma_20,
            "sma_50": self.sma_50,
            "sma_200": self.sma_200,
            "ema_12": self.ema_12,
            "ema_26": self.ema_26,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "rsi_14": self.rsi_14,
            "bollinger_upper": self.bollinger_upper,
            "bollinger_middle": self.bollinger_middle,
            "bollinger_lower": self.bollinger_lower,
            "stochastic_k": self.stochastic_k,
            "stochastic_d": self.stochastic_d,
            "williams_r": self.williams_r,
            "atr": self.atr,
            "golden_cross": self.golden_cross,
            "death_cross": self.death_cross,
            "signal_score": self.signal_score,
            "weights": TA_SIGNAL_WEIGHTS,
        }

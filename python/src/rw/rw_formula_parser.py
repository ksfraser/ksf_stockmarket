"""
rw_formula_parser.py — Research Wizard Formula Parser

Parses RW pre-defined filter formulas into executable filter conditions.

Syntax:
    Comparisons: GT (>), LT (<), GTE (>=), LTE (<=), EQ (=), NEQ (!=)
    Logical:     AND, OR, NOT
    Grouping:    ( )
    Field refs:  price, open, high, low, close, volume, avg_volume,
                 market_cap, pe_ratio, eps, dividend_yield, beta,
                 sma_50, sma_200, rsi_14, macd, bollinger_upper, bollinger_lower,
                 zacks_rank, zacks_consensus, zacks_eps_change
    Literals:    10, 50.5, "string", TRUE, FALSE

Example:
    "Stock Price > 10 AND Relative Volume > 1.5 AND Zacks Rank <= 2"
    -> parsed to: AND(GT(price, 10), AND(GT(relative_volume, 1.5), LTE(zacks_rank, 2)))

Usage:
    from python.src.rw.rw_formula_parser import RwFormulaParser
    parser = RwFormulaParser()
    ast = parser.parse("price GT 10 AND volume GT 1000000")
    results = ast.evaluate(universe_dict)
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

class TokenType(Enum):
    FIELD = "FIELD"         # symbol name reference
    OP = "OP"               # GT, LT, GTE, LTE, EQ, NEQ
    LOGIC = "LOGIC"         # AND, OR, NOT
    LITERAL_NUM = "NUM"     # numeric literal
    LITERAL_STR = "STR"     # string literal
    LITERAL_BOOL = "BOOL"   # TRUE, FALSE
    LPAREN = "("
    RPAREN = ")"
    EOF = "EOF"


@dataclass
class Token:
    type: TokenType
    value: str
    raw: str = ""


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """Tokenizes an RW formula string."""

    # Match patterns in order of specificity
    TOKEN_PATTERNS = [
        ("GTE", r">="),
        ("LTE", r"<="),
        ("NEQ", r"!="),
        ("EQ", r"="),
        ("GT", r">"),
        ("LT", r"<"),
        ("AND", r"\bAND\b"),
        ("OR", r"\bOR\b"),
        ("NOT", r"\bNOT\b"),
        ("STR", r'"[^"]*"|\'[^\']*\''),
        ("BOOL", r"\b(?:TRUE|FALSE)\b"),
        ("NUM", r"\b\d+(?:\.\d+)?\b"),
        ("FIELD", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("SKIP", r"\s+"),
    ]

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.text):
            remaining = self.text[self.pos:]
            matched = False
            for name, pattern in self.TOKEN_PATTERNS:
                m = re.match(pattern, remaining, re.IGNORECASE if name in ("AND", "OR", "NOT", "BOOL") else 0)
                if m:
                    raw = m.group(0)
                    if name == "SKIP":
                        self.pos += len(raw)
                        matched = True
                        break
                    token_type = TokenType[name.upper()] if name.upper() in TokenType.__members__ else TokenType.FIELD
                    if name == "FIELD":
                        # Check if it's actually a keyword we missed
                        upper = raw.upper()
                        if upper in ("AND", "OR", "NOT", "TRUE", "FALSE", "GTE", "LTE", "NEQ", "EQ", "GT", "LT"):
                            token_type = {
                                "AND": TokenType.LOGIC, "OR": TokenType.LOGIC, "NOT": TokenType.LOGIC,
                                "TRUE": TokenType.LITERAL_BOOL, "FALSE": TokenType.LITERAL_BOOL,
                                "GTE": TokenType.OP, "LTE": TokenType.OP, "NEQ": TokenType.OP,
                                "EQ": TokenType.OP, "GT": TokenType.OP, "LT": TokenType.OP,
                            }[upper]
                    elif name == "BOOL":
                        token_type = TokenType.LITERAL_BOOL
                    elif name == "NUM":
                        token_type = TokenType.LITERAL_NUM
                    elif name == "STR":
                        token_type = TokenType.LITERAL_STR
                    elif name == "LPAREN":
                        token_type = TokenType.LPAREN
                    elif name == "RPAREN":
                        token_type = TokenType.RPAREN
                    elif name in ("GTE", "LTE", "NEQ", "EQ", "GT", "LT"):
                        token_type = TokenType.OP

                    self.tokens.append(Token(token_type, raw, raw))
                    self.pos += len(raw)
                    matched = True
                    break
            if not matched:
                raise SyntaxError(f"Unexpected character at position {self.pos}: {remaining[0]!r}")
        self.tokens.append(Token(TokenType.EOF, "", ""))
        return self.tokens


# ---------------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------------

class AstNode(ABC):
    @abstractmethod
    def evaluate(self, row: Dict[str, Any], resolver: "FieldResolver") -> bool:
        ...

    @abstractmethod
    def __repr__(self) -> str:
        ...


@dataclass
class ComparisonNode(AstNode):
    field: str
    op: str  # GT, LT, GTE, LTE, EQ, NEQ
    literal: Union[int, float, str, bool]

    def evaluate(self, row: Dict[str, Any], resolver: "FieldResolver") -> bool:
        val = resolver.resolve(self.field, row)
        if val is None:
            return False
        return _compare(val, self.op, self.literal)

    def __repr__(self) -> str:
        return f"{self.field} {self.op} {self.literal}"


@dataclass
class LogicalAndNode(AstNode):
    left: AstNode
    right: AstNode

    def evaluate(self, row: Dict[str, Any], resolver: "FieldResolver") -> bool:
        return self.left.evaluate(row, resolver) and self.right.evaluate(row, resolver)

    def __repr__(self) -> str:
        return f"({self.left} AND {self.right})"


@dataclass
class LogicalOrNode(AstNode):
    left: AstNode
    right: AstNode

    def evaluate(self, row: Dict[str, Any], resolver: "FieldResolver") -> bool:
        return self.left.evaluate(row, resolver) or self.right.evaluate(row, resolver)

    def __repr__(self) -> str:
        return f"({self.left} OR {self.right})"


@dataclass
class LogicalNotNode(AstNode):
    child: AstNode

    def evaluate(self, row: Dict[str, Any], resolver: "FieldResolver") -> bool:
        return not self.child.evaluate(row, resolver)

    def __repr__(self) -> str:
        return f"NOT({self.child})"


# ---------------------------------------------------------------------------
# Comparison helper
# ---------------------------------------------------------------------------

def _compare(val: Any, op: str, literal: Any) -> bool:
    """Apply comparison operator."""
    # Normalize types
    if isinstance(literal, str):
        # String comparison
        sval = str(val).lower() if val is not None else ""
        slit = literal.lower().strip('"\'')
        if op == "EQ":
            return sval == slit
        if op == "NEQ":
            return sval != slit
        if op == "GT":
            return sval > slit
        if op == "LT":
            return sval < slit
        if op == "GTE":
            return sval >= slit
        if op == "LTE":
            return sval <= slit
    else:
        # Numeric comparison
        try:
            nval = float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            return False
        nlit = float(literal)
        if op == "EQ":
            return nval == nlit
        if op == "NEQ":
            return nval != nlit
        if op == "GT":
            return nval > nlit
        if op == "LT":
            return nval < nlit
        if op == "GTE":
            return nval >= nlit
        if op == "LTE":
            return nval <= nlit
    return False


# ---------------------------------------------------------------------------
# Parser (recursive descent)
# ---------------------------------------------------------------------------

class ParseError(Exception):
    pass


class Parser:
    """Recursive descent parser for RW formula AST."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, expected_type: Optional[TokenType] = None) -> Token:
        token = self.tokens[self.pos]
        if expected_type and token.type != expected_type:
            raise ParseError(f"Expected {expected_type}, got {token.type} ({token.value!r})")
        self.pos += 1
        return token

    def parse(self) -> AstNode:
        """Entry point: parse full expression."""
        node = self._parse_or()
        if self.peek().type != TokenType.EOF:
            raise ParseError(f"Unexpected token after expression: {self.peek().value!r}")
        return node

    # Grammar:
    #   expr     = or_expr
    #   or_expr  = and_expr (OR and_expr)*
    #   and_expr = not_expr (AND not_expr)*
    #   not_expr = NOT not_expr | comparison
    #   comparison = field OP literal | LPAREN expr RPAREN

    def _parse_or(self) -> AstNode:
        left = self._parse_and()
        while self.peek().type == TokenType.LOGIC and self.peek().value.upper() == "OR":
            self.consume(TokenType.LOGIC)
            right = self._parse_and()
            left = LogicalOrNode(left, right)
        return left

    def _parse_and(self) -> AstNode:
        left = self._parse_not()
        while self.peek().type == TokenType.LOGIC and self.peek().value.upper() == "AND":
            self.consume(TokenType.LOGIC)
            right = self._parse_not()
            left = LogicalAndNode(left, right)
        return left

    def _parse_not(self) -> AstNode:
        if self.peek().type == TokenType.LOGIC and self.peek().value.upper() == "NOT":
            self.consume(TokenType.LOGIC)
            child = self._parse_not()
            return LogicalNotNode(child)
        return self._parse_comparison()

    def _parse_comparison(self) -> AstNode:
        token = self.peek()

        if token.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            expr = self._parse_or()
            self.consume(TokenType.RPAREN)
            return expr

        if token.type == TokenType.FIELD:
            field_name = token.value
            self.consume(TokenType.FIELD)
            op_token = self.consume(TokenType.OP)
            op = op_token.value.upper()
            lit_token = self.consume()
            if lit_token.type == TokenType.EOF:
                raise ParseError(f"Expected literal after {op}, got EOF")
            literal: Any
            if lit_token.type == TokenType.LITERAL_NUM:
                literal = float(lit_token.value) if "." in lit_token.value else int(lit_token.value)
            elif lit_token.type == TokenType.LITERAL_STR:
                literal = lit_token.value.strip('"\'케빈')
            elif lit_token.type == TokenType.LITERAL_BOOL:
                literal = lit_token.value.upper() == "TRUE"
            else:
                raise ParseError(f"Expected literal, got {lit_token.type}")
            return ComparisonNode(field_name, op, literal)

        raise ParseError(f"Unexpected token in comparison: {token.value!r} ({token.type})")


# ---------------------------------------------------------------------------
# Field Resolver
# ---------------------------------------------------------------------------

class FieldResolver:
    """
    Resolves RW field names to values from a data row.

    Includes built-in mappings for common RW field names to computed values.
    Subclass or replace resolve() for custom field bindings.
    """

    # Built-in field name normalization: RW display name -> DB column / function
    FIELD_MAPPINGS = {
        # Price fields
        "price": "close",
        "close": "close",
        "open": "open",
        "high": "high",
        "low": "low",
        "volume": "volume",
        "avg_volume": "_avg_volume",
        "relative_volume": "_relative_volume",
        # Fundamental fields
        "market_cap": "market_cap",
        "pe_ratio": "_pe_ratio",
        "eps": "eps",
        "eps_growth": "_eps_growth",
        "dividend_yield": "_dividend_yield",
        "beta": "beta",
        # Technical indicators
        "sma_50": "sma_50",
        "sma_200": "sma_200",
        "rsi_14": "rsi_14",
        "macd": "_macd",
        "bollinger_upper": "bollinger_upper",
        "bollinger_lower": "bollinger_lower",
        "bollinger_mid": "bollinger_mid",
        # Zacks fields
        "zacks_rank": "zacks_rank",
        "zacks_consensus": "zacks_consensus",
        "zacks_eps_change": "zacks_eps_change",
        "zacks_eps_growth": "_zacks_eps_growth",
        # Generic
        "name": "name",
        "sector": "sector",
        "industry": "industry",
    }

    # Computed fields that need special handling
    COMPUTED_FIELDS = {
        "_avg_volume": lambda row, lookback: _compute_avg_volume(row, lookback),
        "_relative_volume": lambda row, lookback: _compute_relative_volume(row, lookback),
        "_pe_ratio": lambda row, lookback: _compute_pe_ratio(row),
        "_eps_growth": lambda row, lookback: _compute_eps_growth(row),
        "_dividend_yield": lambda row, lookback: _compute_dividend_yield(row),
        "_macd": lambda row, lookback: _compute_macd(row),
        "_zacks_eps_growth": lambda row, lookback: _compute_zacks_eps_growth(row),
    }

    def __init__(self, lookback_days: int = 252):
        self.lookback = lookback_days

    def resolve(self, field_name: str, row: Dict[str, Any]) -> Any:
        """Resolve a field name to its value for the given row."""
        normalized = self.FIELD_MAPPINGS.get(field_name.lower(), field_name.lower())

        # Check computed fields
        if normalized in self.COMPUTED_FIELDS:
            try:
                return self.COMPUTED_FIELDS[normalized](row, self.lookback)
            except Exception:
                return None

        # Direct field access
        if normalized in row:
            return row[normalized]

        # Try case-insensitive lookup
        for key, val in row.items():
            if key.lower() == normalized:
                return val

        return None

    def get_field_mapping(self) -> Dict[str, str]:
        """Return a copy of the field mapping dict."""
        return dict(self.FIELD_MAPPINGS)


# ---------------------------------------------------------------------------
# Computed field helpers
# ---------------------------------------------------------------------------

def _compute_avg_volume(row: Dict[str, Any], lookback: int) -> Optional[float]:
    """Compute average volume over lookback period from price history."""
    history = row.get("_price_history")
    if not history:
        return None
    recent = history[-lookback:] if len(history) >= lookback else history
    if not recent:
        return None
    volumes = [h.get("volume", 0) or 0 for h in recent]
    return sum(volumes) / len(volumes) if volumes else None


def _compute_relative_volume(row: Dict[str, Any], lookback: int) -> Optional[float]:
    """Compute relative volume = current_volume / avg_volume."""
    avg = _compute_avg_volume(row, lookback)
    current = row.get("volume") or 0
    if avg and avg > 0:
        return current / avg
    return None


def _compute_pe_ratio(row: Dict[str, Any]) -> Optional[float]:
    close = row.get("close") or 0
    eps = row.get("eps") or 0
    if eps and eps != 0:
        return close / eps
    return None


def _compute_eps_growth(row: Dict[str, Any]) -> Optional[float]:
    eps_current = row.get("eps") or 0
    eps_prior = row.get("eps_prior") or eps_current
    if eps_prior and eps_prior != 0:
        return ((eps_current - eps_prior) / abs(eps_prior)) * 100
    return None


def _compute_dividend_yield(row: Dict[str, Any]) -> Optional[float]:
    annual_div = row.get("annual_dividend") or 0
    close = row.get("close") or 1
    if close > 0:
        return (annual_div / close) * 100
    return None


def _compute_macd(row: Dict[str, Any]) -> Optional[float]:
    ema12 = row.get("ema_12") or 0
    ema26 = row.get("ema_26") or 0
    return ema12 - ema26


def _compute_zacks_eps_growth(row: Dict[str, Any]) -> Optional[float]:
    return row.get("zacks_eps_change") or row.get("eps_growth")


# ---------------------------------------------------------------------------
# Main Parser class (convenience wrapper)
# ---------------------------------------------------------------------------

class RwFormulaParser:
    """
    Convenience class for parsing and executing RW formulas.

    Caches parsed ASTs by formula text hash for performance.
    """

    def __init__(self, field_resolver: Optional[FieldResolver] = None):
        self._cache: Dict[str, AstNode] = {}
        self._resolver = field_resolver or FieldResolver()

    def parse(self, formula_text: str) -> AstNode:
        """Parse a formula string into an AST, using cache if available."""
        cache_key = formula_text.strip().lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        lexer = Lexer(formula_text)
        tokens = lexer.tokenize()

        # Debug: log tokens
        logger.debug("Tokens for '%s': %s", formula_text, [(t.type.name, t.value) for t in tokens if t.type != TokenType.SKIP and t.type != TokenType.EOF])

        parser = Parser(tokens)
        try:
            ast = parser.parse()
        except ParseError as exc:
            logger.error("Parse error for '%s': %s", formula_text, exc)
            raise

        self._cache[cache_key] = ast
        return ast

    def evaluate(self, formula_text: str, row: Dict[str, Any]) -> bool:
        """Parse and evaluate a formula against a single row."""
        ast = self.parse(formula_text)
        return ast.evaluate(row, self._resolver)

    def evaluate_batch(self, formula_text: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate a formula against multiple rows, return matching rows."""
        ast = self.parse(formula_text)
        return [row for row in rows if ast.evaluate(row, self._resolver)]

    def clear_cache(self) -> None:
        """Clear the parse cache."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        return len(self._cache)


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

    test_formulas = [
        "price GT 10",
        "price GT 10 AND volume GT 1000000",
        "(pe_ratio LT 15 OR dividend_yield GT 3) AND zacks_rank LTE 2",
        "NOT (zacks_rank GT 3)",
        "price GT 10 AND (volume GT 500000 OR avg_volume GT 1000000)",
    ]

    parser = RwFormulaParser()
    resolver = FieldResolver()

    # Sample test row
    test_row = {
        "symbol": "RY.TO",
        "close": 190.50,
        "open": 188.00,
        "high": 192.00,
        "low": 187.50,
        "volume": 2500000,
        "avg_volume": 2000000,
        "market_cap": 150000000000,
        "pe_ratio": 12.5,
        "eps": 15.24,
        "eps_prior": 14.00,
        "dividend_yield": 4.2,
        "beta": 1.1,
        "sma_50": 185.00,
        "sma_200": 170.00,
        "rsi_14": 62.5,
        "ema_12": 189.00,
        "ema_26": 187.50,
        "bollinger_upper": 195.00,
        "bollinger_lower": 180.00,
        "bollinger_mid": 187.50,
        "zacks_rank": 2,
        "zacks_consensus": "Buy",
        "zacks_eps_change": 8.5,
        "name": "Royal Bank of Canada",
        "sector": "Financials",
        "industry": "Banks",
        "_price_history": [{"volume": 2000000} for _ in range(252)],
    }

    print("=== RW Formula Parser Test ===\n")
    for formula in test_formulas:
        print(f"Formula: {formula}")
        try:
            ast = parser.parse(formula)
            result = ast.evaluate(test_row, resolver)
            matches = parser.evaluate_batch(formula, [test_row])
            print(f"  AST: {ast}")
            print(f"  Result for test row: {result}")
            print(f"  Batch matches: {len(matches)} / 1")
        except ParseError as exc:
            print(f"  PARSE ERROR: {exc}")
        print()

    print(f"Cache size: {parser.cache_size}")

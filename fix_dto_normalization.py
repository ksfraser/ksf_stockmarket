#!/usr/bin/env python3
"""
fix_dto_normalization.py

Rebuild IndicatorDTO in migrate_indicators_json_to_columnar.py so
that dots in JSON keys are collapsed to underscores (bb_10_2.0_lower
== bb_10_2_0_lower). No _dot_ names. Deduplicated canonical keys.

Run this script; it edits migrate_indicators_json_to_columnar.py in place.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path('/home/ksf_stockmarket/ksf_stockmarket/migrate_indicators_json_to_columnar.py')

# 219 raw discovered keys
RAW_KEYS = [
    "ad", "adosc", "adx_14", "adx_21", "adx_7", "adxr_14", "adxr_21", "adxr_7",
    "apo_14", "apo_21", "apo_7", "aroonosc_14", "aroonosc_21", "aroonosc_7",
    "atr_14", "atr_20", "atr_7", "avgprice",
    "bb_10_2.0_lower", "bb_10_2.0_mid", "bb_10_2.0_upper",
    "bb_10_2.5_lower", "bb_10_2.5_mid", "bb_10_2.5_upper",
    "bb_10_2_0_lower", "bb_10_2_0_mid", "bb_10_2_0_upper",
    "bb_10_2_5_lower", "bb_10_2_5_mid", "bb_10_2_5_upper",
    "bb_20_2.0_lower", "bb_20_2.0_mid", "bb_20_2.0_upper",
    "bb_20_2.5_lower", "bb_20_2.5_mid", "bb_20_2.5_upper",
    "bb_20_2_0_lower", "bb_20_2_0_mid", "bb_20_2_0_upper",
    "bb_20_2_5_lower", "bb_20_2_5_mid", "bb_20_2_5_upper",
    "bb_50_1.5_lower", "bb_50_1.5_mid", "bb_50_1.5_upper",
    "bb_50_1_5_lower", "bb_50_1_5_mid", "bb_50_1_5_upper",
    "bb_50_2.0_lower", "bb_50_2.0_mid", "bb_50_2.0_upper",
    "bb_50_2.5_lower", "bb_50_2.5_mid", "bb_50_2.5_upper",
    "bb_50_2_0_lower", "bb_50_2_0_mid", "bb_50_2_0_upper",
    "bb_50_2_5_lower", "bb_50_2_5_mid", "bb_50_2_5_upper",
    "bb_5_2_0_lower", "bb_5_2_0_mid", "bb_5_2_0_upper",
    "bb_5_2_5_lower", "bb_5_2_5_mid", "bb_5_2_5_upper",
    "bop", "cci_14", "cci_21", "cci_7", "cmo_14", "cmo_21", "cmo_7",
    "dema_10", "dema_100", "dema_20", "dema_5", "dema_50", "dema_8",
    "ema_10", "ema_100", "ema_20", "ema_200", "ema_5", "ema_50", "ema_8",
    "high_60", "ht_dcperiod", "ht_dcphase", "ht_leadsine",
    "ht_phasor_inphase", "ht_phasor_quadrature", "ht_sine",
    "ht_sine_leadsine", "ht_sine_sine", "ht_trendline", "ht_trendmode",
    "kama_10", "kama_20", "kama_50",
    "linreg_10", "linreg_14", "linreg_5",
    "linreg_angle_10", "linreg_angle_14", "linreg_intercept_10",
    "linreg_intercept_14", "linreg_intercept_5",
    "linreg_slope_10", "linreg_slope_14",
    "macd", "macd_10_50_10", "macd_12_26_9", "macd_12_26_9_hist",
    "macd_12_26_9_histogram", "macd_12_26_9_macd", "macd_12_26_9_signal",
    "macd_24_52_18_hist", "macd_24_52_18_histogram",
    "macd_24_52_18_macd", "macd_24_52_18_signal",
    "macd_5_35_5", "macd_8_21_5_hist", "macd_8_21_5_histogram",
    "macd_8_21_5_macd", "macd_8_21_5_signal",
    "macd_hist", "macd_hist_10_50_10", "macd_hist_12_26_9", "macd_hist_5_35_5",
    "macd_signal", "macd_signal_10_50_10", "macd_signal_12_26_9", "macd_signal_5_35_5",
    "medprice", "mfi_14", "mfi_21", "mfi_7",
    "mom_14", "mom_21", "mom_7",
    "natr_14", "natr_20", "natr_7",
    "obv", "ppo_14", "ppo_21", "ppo_7",
    "roc_14", "roc_21", "roc_7", "rocp_14", "rocp_21", "rocp_7",
    "rocr100_14", "rocr100_21", "rocr100_7",
    "rocr_14", "rocr_21", "rocr_7",
    "rsi_14", "rsi_21", "rsi_3", "rsi_7",
    "sma_10", "sma_100", "sma_20", "sma_200", "sma_5", "sma_50", "sma_8",
    "stddev_10", "stddev_14", "stddev_5",
    "stoch_14_3_3_d", "stoch_14_3_3_k", "stoch_21_5_5_d", "stoch_21_5_5_k",
    "stoch_5_3_3_d", "stoch_5_3_3_k",
    "stoch_d_14", "stoch_d_5", "stoch_k_14", "stoch_k_5",
    "tema_10", "tema_100", "tema_20", "tema_5", "tema_50", "tema_8",
    "trange", "trima_10", "trima_100", "trima_20", "trima_5", "trima_50", "trima_8",
    "trix_14", "trix_21", "trix_7",
    "tsf_10", "tsf_14", "tsf_5",
    "typprice", "var_10", "var_14", "var_5",
    "vwap", "wclprice", "willr_14", "willr_21", "willr_7",
    "wma_10", "wma_100", "wma_20", "wma_200", "wma_5", "wma_50", "wma_8",
]

def normalize(key):
    """Collapse dots to underscores. bb_10_2.0_lower -> bb_10_2_0_lower."""
    return key.replace('.', '_')

# Deduplicate
CANON = sorted(set(normalize(k) for k in RAW_KEYS))
N_IND = len(CANON)
N_TOTAL = N_IND + 2  # + symbol, price_date

print(f"Raw keys: {len(RAW_KEYS)}")
print(f"Canonical (after normalize+dedup): {N_IND}")
print(f"Total fields: {N_TOTAL}")
print(f"Collapsed {len(RAW_KEYS) - N_IND} separator duplicates.")
print()

def setter_c(name):
    return (
        f"    @_setter\n"
        f"    def set_{name}(self, v):\n"
        f"        self.{name} = v\n"
    )

setter_blocks = "\n".join(setter_c(c) for c in CANON)

class_text = f"""class IndicatorDTO:
    \"\"\"Explicit contract: every indicator key has a field + a setter.\"\"\"

    __fields__ = []  # populated at module load below

    @staticmethod
    def _setter(fn):
        fn._is_indicator_setter = True
        return fn

    # ---- Structural (always present, handled specially) ----
    @_setter
    def set_symbol(self, v):
        self.symbol = v

    @_setter
    def set_price_date(self, v):
        self.price_date = v

    # ---- Discovered indicator keys (auto-generated from indicators_json) ----
    # Every key below was found in the live indicators_json table.
    # Keys that use '.' as separator are normalized to '_' so that e.g.
    # bb_10_2.0_lower and bb_10_2_0_lower are the SAME DTO field.

{setter_blocks}
    def __init__(self):
        # Auto-initialize all fields to None.
        for _field in IndicatorDTO.__fields__:
            setattr(self, _field, None)

    def __repr__(self):
        return (
            f"IndicatorDTO(symbol={{self.symbol!r}}, price_date={{self.price_date!r}}, "
            f"fields_set={{sum(1 for f in self.__fields__ if getattr(self, f, None) is not None)}})"
        )

    def field_names(self):
        \"\"\"Return all DTO field names (excluding structural).\"\"\"
        return [f for f in self.__fields__ if f not in {'set_symbol', 'set_price_date'}]

    # ---- Key mapping (JSON key -> canonical setter/field name) ----
    _KEY_MAP = {{}}

    @staticmethod
    def _sanitize_key(key: str) -> str:
        \"\"\"Map a JSON key to the corresponding DTO setter/field name.
        Normalizes dots to underscores so bb_10_2.0_lower and
        bb_10_2_0_lower both map to the same field.\"\"\"
        if key in IndicatorDTO._KEY_MAP:
            return IndicatorDTO._KEY_MAP[key]
        canon = key.replace('.', '_')
        IndicatorDTO._KEY_MAP[key] = canon
        return canon

    def from_json(self, data):
        \"\"\"Parse a JSON object (dict) into this DTO.
        Raises ValueError on the FIRST key that has no matching setter,
        printing the exact key name and value.\"\"\"
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {{type(data).__name__}}")
        seen = set()
        for key, value in data.items():
            setter_name = 'set_' + IndicatorDTO._sanitize_key(key)
            setter = getattr(self, setter_name, None)
            if setter is None:
                available = sorted(self.__fields__)
                raise ValueError(
                    f"JSON key has no DTO field: {{key!r}}\\n"
                    f"  value = {{value!r}}\\n"
                    f"  type  = {{type(value).__name__}}\\n"
                    f"  Add a setter 'set_{{IndicatorDTO._sanitize_key(key)}}' to IndicatorDTO, then re-run.\\n"
                    f"  Available DTO fields ({{len(available)}}): {{available[:20]}}{{('...' if len(available) > 20 else '')}}\"
                )
            setter(self, value)
            seen.add(key)
        return self

    def to_dict(self):
        \"\"\"Return dict mapping canonical field names -> values (only non-None).\"\"\"
        d = {{}}
        for field in self.__fields__:
            val = getattr(self, field, None)
            if val is not None:
                d[field] = val
        return d
"""

# Read current file
src = SRC.read_text(encoding='utf-8')

# Find and replace the class
class_start = src.find("class IndicatorDTO:")
assert class_start != -1, "class IndicatorDTO: not found"

marker = "\n# ---------------------------------------------------------------------------\n# DB helpers"
marker_idx = src.find(marker, class_start)
assert marker_idx != -1, "DB helpers marker not found after class"

new_src = src[:class_start] + class_text + "\n\n" + src[marker_idx:]

# Update the assertion at the bottom
old_assert_pat = re.compile(
    r"IndicatorDTO\.__fields__ = sorted\(_IndicatorDTO_setters\)\n"
    r"assert len\(IndicatorDTO\.__fields__\) == \d+.*?(?=\n\n\ndef to_decimal_safe|\Z)",
    re.S,
)
m = old_assert_pat.search(new_src)
if m:
    new_assert = (
        f"IndicatorDTO.__fields__ = sorted(_IndicatorDTO_setters)\n"
        f"assert len(IndicatorDTO.__fields__) >= {N_TOTAL}, (\n"
        f"    f\"Expected at least {N_TOTAL} DTO fields ({N_IND} discovered + symbol + price_date), \"\n"
        f"    f\"got {{len(IndicatorDTO.__fields__)}}. A setter is missing.\"\n"
        f")\n"
        f"print(f\"IndicatorDTO.__fields__ = {{len(IndicatorDTO.__fields__)}} fields\")\n"
        f"print(f\"  Discovered indicators: {{len(_IndicatorDTO_setters) - 2}}\")\n"
        f"\n"
    )
    new_src = new_src[:m.start()] + new_assert + new_src[m.end():]
    print("Updated assertion.")
else:
    print("WARNING: Could not find old assertion — may need manual update.")

SRC.write_text(new_src, encoding='utf-8')
print(f"\nWrote {SRC}. Ready for syntax check + first run.")

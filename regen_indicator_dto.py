#!/usr/bin/env python3
"""
Regenerate the IndicatorDTO section of migrate_indicators_json_to_columnar.py.

Reads the discovery output (219 distinct keys) and inserts:
- All 219 setter methods
- An auto-initializing __init__
- A working __fields__ computation at module load time
- Keeps the structural setters (symbol, price_date, adjclose) that already exist
"""
import re
import os

SOURCE = os.path.join(os.path.dirname(__file__), 'migrate_indicators_json_to_columnar.py')

# 219 distinct keys discovered by discover_indicators_json_keys.py
DISCOVERED_KEYS = {
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
}

# Structural keys (always present, handled specially)
STRUCTURAL = {"symbol", "price_date"}

def sanitize_field_name(key: str) -> str:
    """Convert a JSON key (may contain dots) to a valid, readable Python identifier.

    Only '.' is special-cased (replaced with '_dot_'). All other chars are
    already identifier-safe for the keys we've seen ([a-z0-9_\.]).
    """
    if '.' in key:
        return key.replace('.', '_dot_')
    return key


def generate_setter(key):
    field = sanitize_field_name(key)
    lines = [
        f"    @_setter",
        f"    def set_{field}(self, v):",
        f"        self.{field} = v",
        f"",
    ]
    return "\n".join(lines)

def generate_init_assignments():
    lines = []
    for key in sorted(DISCOVERED_KEYS):
        lines.append(f"        self.{key} = None  # discovered key")
    return "\n".join(lines)

# Read current source
with open(SOURCE) as f:
    src = f.read()

# 1. Replace __init__ with auto-init version
old_init_pat = re.compile(
    r"    def __init__\(self\):\n"
    r"(?:        [^\n]*\n)+"          # any number of indented init lines
    r"(?=\n    def __repr__)",        # stop before __repr__
    re.M,
)
new_init = (
    "    def __init__(self):\n"
    "        # Auto-initialize all discovered indicator fields to None.\n"
    "        # Any new key discovered later just needs a setter added above;\n"
    "        # this init picks it up automatically.\n"
    "        for _field in IndicatorDTO.__fields__:\n"
    "            setattr(self, _field, None)\n"
    "\n"
)
src2, n = old_init_pat.subn(new_init, src, count=1)
assert n == 1, f"Expected 1 __init__ replacement, got {n}"

# 2. Replace __repr__ to use __fields__
old_repr = '''    def __repr__(self):
        return (
            f"IndicatorDTO(symbol={self.symbol!r}, price_date={self.price_date!r}, "
            f"fields_set={sum(1 for f in self.__fields__ if getattr(self, f, None) is not None)})"
        )

    def field_names(self):
        """Return all DTO field names (excluding structural)."""
        skip = {'set_symbol', 'set_price_date', 'set_adjclose'}
        return [f for f in self.__fields__ if f not in skip]

    def to_dict(self):
        d = {}
        for field in self.__fields__:
            val = getattr(self, field, None)
            if val is not None:
                d[field] = val
        return d

    def from_json(self, data):'''

new_repr_block = old_repr  # keep as-is (uses __fields__ which will be set)

# 3. Replace the @_setter registration comment + broken subclass hook
#    with a working module-level __fields__ computation.
# Find the block after the class that starts with "class IndicatorDTO"
# and find the __init_subclass__ method.

# The broken __init_subclass__ block:
old_subclass = '''    @staticmethod
    def _setter(fn):
        fn._is_indicator_setter = True
        return fn

    # ---- Structural ----
    @_setter
    def set_symbol(self, v):
        self.symbol = v

    @_setter
    def set_price_date(self, v):
        self.price_date = v

    # ---- Existing 139 indicator columns (representative subset; the rest
    #      are added automatically by the migration when they appear) ----
    # The script discovers the real column list from the table at runtime
    # and maps DTO fields to columns by name. The DTO must define a setter
    # for every JSON key; the table may lag behind. When a JSON key appears
    # that has no setter, the script stops and tells you the exact key.

    @_setter
    def set_adjclose(self, v):
        self.adjclose = v'''

new_subclass = '''    @staticmethod
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
    # If a new key appears later, add its setter here and re-run.'''

# Insert discovery-generated setters after the structural ones
setter_block = new_subclass + "\n\n" + "\n".join(generate_setter(k) for k in sorted(DISCOVERED_KEYS))

# Find the old block and replace
idx = src2.find(old_subclass)
assert idx != -1, "Could not find old_subclass block in source"
src3 = src2[:idx] + setter_block + src2[idx + len(old_subclass):]

# 4. Replace __init_subclass__ with module-level __fields__ computation.
# Find "    __fields__ = []  # populated by __init_subclass__ / setattr registration\n\n    @staticmethod"
old_classvar = '''    __fields__ = []  # populated by __init_subclass__ / setattr registration

    @staticmethod
    def _setter(fn):'''
new_classvar = '''    # __fields__ computed at module load below; must be set before any
    # IndicatorDTO instance is created.
    __fields__ = []

    @staticmethod
    def _setter(fn):'''

src4 = src3.replace(old_classvar, new_classvar, 1)

# 5. After the class definition ends (find "def to_decimal_safe"), insert __fields__ computation
insertion_marker = "\n\ndef to_decimal_safe(v):"
fields_computation = f'''
# ---------------------------------------------------------------------------
# Compute IndicatorDTO.__fields__ at module load time.
# Scans the class for all methods marked with _is_indicator_setter.
# This is the authoritative list of DTO fields.
# ---------------------------------------------------------------------------
_IndicatorDTO_setters = [
    name for name in dir(IndicatorDTO)
    if not name.startswith('_')
    and callable(getattr(IndicatorDTO, name, None))
    and getattr(getattr(IndicatorDTO, name), '_is_indicator_setter', False)
]
IndicatorDTO.__fields__ = sorted(_IndicatorDTO_setters)
assert len(IndicatorDTO.__fields__) == {len(DISCOVERED_KEYS) + 1}, (
    f"Expected {len(DISCOVERED_KEYS) + 1} DTO fields (219 discovered + symbol), "
    f"got {{len(IndicatorDTO.__fields__)}}. A setter is missing."
)

'''
src5 = src4.replace(insertion_marker, fields_computation + insertion_marker, 1)

# 6. Remove the broken subclass hook body (the __init_subclass__ def and its body)
old_subclass_def = '''    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__fields__ = []
        for attr in dir(cls):
            if attr.startswith('_'):
                continue
            val = getattr(cls, attr)
            if callable(val) and getattr(val, '_is_indicator_setter', False):
                cls.__fields__.append(attr)

'''
src6 = src5.replace(old_subclass_def, "", 1)

with open(SOURCE, 'w') as f:
    f.write(src6)

print(f"Regenerated IndicatorDTO in {SOURCE}")
print(f"  Added {len(DISCOVERED_KEYS)} setter methods")
print(f"  Replaced __init__ with auto-init")
print(f"  Installed module-level __fields__ computation")
print(f"  Expected total fields: {len(DISCOVERED_KEYS) + 1} (219 + symbol)")

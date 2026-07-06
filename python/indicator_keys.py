#!/usr/bin/env python3
"""
Indicator Key Registry — Single Source of Truth for indicator JSON keys.

This module defines the canonical indicator key names used throughout the system.
Both the indicator calculator (writer) and templates/consumers (readers) should
import from here to ensure consistency.

Key naming convention: {indicator}_{params}_{variant}
- indicator: base name (rsi, macd, stoch, bb, atr, etc.)
- params: parameter string (e.g., "14", "12_26_9", "20_2.0")
- variant: output variant (macd, signal, hist, k, d, upper, mid, lower)

All keys are lowercase with underscores.
"""

# ── Canonical Indicator Key Definitions ────────────────────────────────────

# RSI
RSI_KEYS = {
    'rsi_3': 'rsi_3',
    'rsi_7': 'rsi_7',
    'rsi_14': 'rsi_14',
    'rsi_21': 'rsi_21',
}

# MACD - primary (12,26,9) is the standard
MACD_KEYS = {
    'macd_12_26_9_macd': 'macd_12_26_9_macd',
    'macd_12_26_9_signal': 'macd_12_26_9_signal',
    'macd_12_26_9_hist': 'macd_12_26_9_hist',
    # Additional MACD variants
    'macd_8_21_5_macd': 'macd_8_21_5_macd',
    'macd_8_21_5_signal': 'macd_8_21_5_signal',
    'macd_8_21_5_hist': 'macd_8_21_5_hist',
    'macd_24_52_18_macd': 'macd_24_52_18_macd',
    'macd_24_52_18_signal': 'macd_24_52_18_signal',
    'macd_24_52_18_hist': 'macd_24_52_18_hist',
}

# Stochastic
STOCH_KEYS = {
    'stoch_5_3_3_k': 'stoch_5_3_3_k',
    'stoch_5_3_3_d': 'stoch_5_3_3_d',
    'stoch_14_3_3_k': 'stoch_14_3_3_k',
    'stoch_14_3_3_d': 'stoch_14_3_3_d',
    'stoch_21_5_5_k': 'stoch_21_5_5_k',
    'stoch_21_5_5_d': 'stoch_21_5_5_d',
}

# Bollinger Bands
BB_KEYS = {}
for period in [5, 10, 20, 50]:
    for std in [1.5, 2.0, 2.5]:
        std_key = str(std).replace('.', '_')  # 2.0 -> 2_0
        BB_KEYS[f'bb_{period}_{std_key}_upper'] = f'bb_{period}_{std_key}_upper'
        BB_KEYS[f'bb_{period}_{std_key}_mid'] = f'bb_{period}_{std_key}_mid'
        BB_KEYS[f'bb_{period}_{std_key}_lower'] = f'bb_{period}_{std_key}_lower'

# ATR / NATR
ATR_KEYS = {
    'atr_7': 'atr_7',
    'atr_14': 'atr_14',
    'atr_20': 'atr_20',
    'natr_7': 'natr_7',
    'natr_14': 'natr_14',
    'natr_20': 'natr_20',
    'trange': 'trange',
}

# ADX / ADXR
ADX_KEYS = {
    'adx_7': 'adx_7',
    'adx_14': 'adx_14',
    'adx_21': 'adx_21',
    'adxr_7': 'adxr_7',
    'adxr_14': 'adxr_14',
    'adxr_21': 'adxr_21',
}

# Moving Averages
MA_KEYS = {}
for ma_type in ['sma', 'ema', 'wma', 'tema', 'dema', 'trima', 'kama']:
    for period in [5, 8, 10, 20, 50, 100, 200]:
        if ma_type in ('tema', 'dema', 'trima') and period == 200:
            continue
        MA_KEYS[f'{ma_type}_{period}'] = f'{ma_type}_{period}'

# Price Transforms
PRICE_KEYS = {
    'avgprice': 'avgprice',
    'medprice': 'medprice',
    'typprice': 'typprice',
    'wclprice': 'wclprice',
    'bop': 'bop',
}

# Hilbert Transform
HT_KEYS = {
    'ht_trendline': 'ht_trendline',
    'ht_trendmode': 'ht_trendmode',
    'ht_dcperiod': 'ht_dcperiod',
    'ht_dcphase': 'ht_dcphase',
    'ht_phasor_inphase': 'ht_phasor_inphase',
    'ht_phasor_quadrature': 'ht_phasor_quadrature',
    'ht_sine_sine': 'ht_sine_sine',
    'ht_sine_leadsine': 'ht_sine_leadsine',
}

# ROC / Momentum family
ROC_KEYS = {}
for base in ['roc', 'rocp', 'rocr', 'rocr100', 'mom']:
    for p in [7, 14, 21]:
        ROC_KEYS[f'{base}_{p}'] = f'{base}_{p}'

# PPO / APO
PPO_APO_KEYS = {}
for p in [7, 14, 21]:
    PPO_APO_KEYS[f'ppo_{p}'] = f'ppo_{p}'
    PPO_APO_KEYS[f'apo_{p}'] = f'apo_{p}'

# Volume indicators
VOL_KEYS = {
    'ad': 'ad',
    'adosc': 'adosc',
    'obv': 'obv',
}

# Linear Regression / TSF
LR_KEYS = {}
for p in [5, 10, 14]:
    LR_KEYS[f'linreg_{p}'] = f'linreg_{p}'
    LR_KEYS[f'linreg_intercept_{p}'] = f'linreg_intercept_{p}'
    LR_KEYS[f'tsf_{p}'] = f'tsf_{p}'
for p in [10, 14]:
    LR_KEYS[f'linreg_slope_{p}'] = f'linreg_slope_{p}'
    LR_KEYS[f'linreg_angle_{p}'] = f'linreg_angle_{p}'

# Standard Deviation / Variance
STAT_KEYS = {}
for p in [5, 10, 14]:
    STAT_KEYS[f'stddev_{p}'] = f'stddev_{p}'
    STAT_KEYS[f'var_{p}'] = f'var_{p}'

# CCI / CMO / MFI / WILLR / AROONOSC / TRIX / PPO
OTHER_KEYS = {}
for p in [7, 14, 21]:
    OTHER_KEYS[f'cci_{p}'] = f'cci_{p}'
    OTHER_KEYS[f'cmo_{p}'] = f'cmo_{p}'
    OTHER_KEYS[f'mfi_{p}'] = f'mfi_{p}'
    OTHER_KEYS[f'willr_{p}'] = f'willr_{p}'
    OTHER_KEYS[f'aroonosc_{p}'] = f'aroonosc_{p}'
    OTHER_KEYS[f'trix_{p}'] = f'trix_{p}'

# ── Master Registry ────────────────────────────────────────────────────────

ALL_KEYS = {}
ALL_KEYS.update(RSI_KEYS)
ALL_KEYS.update(MACD_KEYS)
ALL_KEYS.update(STOCH_KEYS)
ALL_KEYS.update(BB_KEYS)
ALL_KEYS.update(ATR_KEYS)
ALL_KEYS.update(ADX_KEYS)
ALL_KEYS.update(MA_KEYS)
ALL_KEYS.update(PRICE_KEYS)
ALL_KEYS.update(HT_KEYS)
ALL_KEYS.update(ROC_KEYS)
ALL_KEYS.update(PPO_APO_KEYS)
ALL_KEYS.update(VOL_KEYS)
ALL_KEYS.update(LR_KEYS)
ALL_KEYS.update(STAT_KEYS)
ALL_KEYS.update(OTHER_KEYS)

# ── Aliases (for backward compatibility) ──────────────────────────────────

# Maps legacy keys → canonical keys
ALIASES = {
    # MACD legacy
    'macd': 'macd_12_26_9_macd',
    'macd_signal': 'macd_12_26_9_signal',
    'macd_hist': 'macd_12_26_9_hist',
    'macd_12_26_9': 'macd_12_26_9_macd',  # ambiguous, map to macd line
    'macd_signal_12_26_9': 'macd_12_26_9_signal',
    'macd_hist_12_26_9': 'macd_12_26_9_hist',
    
    # Stochastic legacy
    'stoch_k_14': 'stoch_14_3_3_k',
    'stoch_d_14': 'stoch_14_3_3_d',
    'stoch_k_5': 'stoch_5_3_3_k',
    'stoch_d_5': 'stoch_5_3_3_d',
    
    # BB legacy (2.0 vs 2_0)
    'bb_20_2.0_upper': 'bb_20_2_0_upper',
    'bb_20_2.0_mid': 'bb_20_2_0_mid',
    'bb_20_2.0_lower': 'bb_20_2_0_lower',
    'bb_20_2.5_upper': 'bb_20_2_5_upper',
    'bb_20_2.5_mid': 'bb_20_2_5_mid',
    'bb_20_2.5_lower': 'bb_20_2_5_lower',
    'bb_10_2.0_upper': 'bb_10_2_0_upper',
    'bb_10_2.0_mid': 'bb_10_2_0_mid',
    'bb_10_2.0_lower': 'bb_10_2_0_lower',
    'bb_10_2.5_upper': 'bb_10_2_5_upper',
    'bb_10_2.5_mid': 'bb_10_2_5_mid',
    'bb_10_2.5_lower': 'bb_10_2_5_lower',
    'bb_50_1.5_upper': 'bb_50_1_5_upper',
    'bb_50_1.5_mid': 'bb_50_1_5_mid',
    'bb_50_1.5_lower': 'bb_50_1_5_lower',
    'bb_50_2.0_upper': 'bb_50_2_0_upper',
    'bb_50_2.0_mid': 'bb_50_2_0_mid',
    'bb_50_2.0_lower': 'bb_50_2_0_lower',
    'bb_50_2.5_upper': 'bb_50_2_5_upper',
    'bb_50_2.5_mid': 'bb_50_2_5_mid',
    'bb_50_2.5_lower': 'bb_50_2_5_lower',
}

# Reverse lookup: canonical -> [legacy keys that map to it]
REVERSE_ALIASES = {}
for legacy, canonical in ALIASES.items():
    REVERSE_ALIASES.setdefault(canonical, []).append(legacy)


def get_canonical_key(key: str) -> str:
    """Resolve a key to its canonical form."""
    return ALIASES.get(key, key)


def get_all_forms(canonical_key: str) -> list:
    """Get all key forms (canonical + legacy) for a given canonical key."""
    return [canonical_key] + REVERSE_ALIASES.get(canonical_key, [])


def resolve_indicator_dict(data: dict) -> dict:
    """
    Given a raw indicator dict from the database, return a new dict with
    both canonical keys AND legacy aliases populated.
    
    This ensures templates can use either naming convention.
    """
    result = dict(data)  # start with original
    
    for legacy, canonical in ALIASES.items():
        if legacy in data and canonical not in result:
            result[canonical] = data[legacy]
        elif canonical in data and legacy not in result:
            result[legacy] = data[canonical]
    
    return result


# ── Template Helper (for PHP) ──────────────────────────────────────────────

# PHP array of canonical keys for easy inclusion
PHP_CANONICAL_KEYS = {
    'RSI': list(RSI_KEYS.values()),
    'MACD': list(MACD_KEYS.values()),
    'STOCH': list(STOCH_KEYS.values()),
    'BB': list(BB_KEYS.values()),
    'ATR': list(ATR_KEYS.values()),
    'ADX': list(ADX_KEYS.values()),
    'MA': list(MA_KEYS.values()),
    'PRICE': list(PRICE_KEYS.values()),
    'HT': list(HT_KEYS.values()),
    'ROC': list(ROC_KEYS.values()),
    'PPO_APO': list(PPO_APO_KEYS.values()),
    'VOL': list(VOL_KEYS.values()),
    'LR': list(LR_KEYS.values()),
    'STAT': list(STAT_KEYS.values()),
    'OTHER': list(OTHER_KEYS.values()),
}


if __name__ == '__main__':
    import json
    print(f"Total canonical keys: {len(ALL_KEYS)}")
    print(f"Total aliases: {len(ALIASES)}")
    print()
    print("Sample MACD keys:", MACD_KEYS)
    print("Sample STOCH keys:", STOCH_KEYS)
    print("Sample BB keys (20):", {k:v for k,v in BB_KEYS.items() if k.startswith('bb_20')})
    print("Aliases:", ALIASES)
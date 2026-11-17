#!/usr/bin/env python3
"""
Advanced Technical Pattern Recognition & Indicators
====================================================

Adds to existing TechnicalAnalyzer:
- Chart patterns: Head & Shoulders, Double Top, Diamond Top, Triangle, Wedge
- Gap detection (gap up/down)
- CCI (Commodity Channel Index)
- Williams %R
- Fast Stochastic
- Short Term KST (Know Sure Thing)
- Triple MA Crossover (4-9-18 day)
- Pattern confidence scoring
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)


class AdvancedPatternAnalyzer:
    """
    Detects chart patterns and calculates advanced technical indicators.
    All methods are static and operate on OHLCV DataFrames.
    """

    # =========================================================================
    # CHART PATTERN RECOGNITION
    # =========================================================================

    @staticmethod
    def find_head_and_shoulders(high: pd.Series, low: pd.Series, close: pd.Series,
                                 window: int = 60) -> Dict:
        """
        Detect Head & Shoulders top pattern.
        
        Structure: Left Shoulder (peak) → Head (higher peak) → Right Shoulder (lower peak)
        with a neckline connecting the two troughs between them.
        
        Returns pattern info with confidence score.
        """
        result = {'detected': False, 'confidence': 0, 'type': 'head_and_shoulders_top',
                  'neckline': None, 'target': None, 'details': []}

        if len(close) < window:
            return result

        # Use recent window
        h = high.tail(window).values
        l = low.tail(window).values
        c = close.tail(window).values

        # Find local maxima (peaks) using scipy-like approach
        peaks = AdvancedPatternAnalyzer._find_peaks(h, order=5)
        troughs = AdvancedPatternAnalyzer._find_peaks(-l, order=5)

        if len(peaks) < 3 or len(troughs) < 2:
            return result

        # Look for H&S pattern: 3 peaks with middle one highest
        for i in range(len(peaks) - 2):
            left_shoulder = peaks[i]
            head = peaks[i + 1]
            right_shoulder = peaks[i + 2]

            # Head must be higher than both shoulders
            if h[head] > h[left_shoulder] and h[head] > h[right_shoulder]:
                # Shoulders should be roughly symmetric (within 20%)
                shoulder_diff = abs(h[left_shoulder] - h[right_shoulder]) / h[head]
                if shoulder_diff < 0.20:
                    # Find neckline (troughs between shoulders and head)
                    neck_troughs = [t for t in troughs if left_shoulder < t < right_shoulder]
                    if len(neck_troughs) >= 2:
                        neckline = np.mean([l[t] for t in neck_troughs])
                        head_height = h[head] - neckline
                        target = neckline - head_height  # Measured move target

                        # Confidence based on symmetry and volume
                        confidence = max(0, 1.0 - shoulder_diff * 2)

                        # Check if price has broken neckline (confirmation)
                        if c[-1] < neckline:
                            confidence = min(confidence + 0.2, 1.0)
                            result['details'].append("✅ Neckline broken — pattern confirmed")
                        else:
                            result['details'].append(f"⏳ Neckline at ${neckline:.2f} — awaiting breakout")

                        result['detected'] = True
                        result['confidence'] = round(confidence, 2)
                        result['neckline'] = round(neckline, 2)
                        result['target'] = round(target, 2)
                        result['head_price'] = round(h[head], 2)
                        result['left_shoulder'] = round(h[left_shoulder], 2)
                        result['right_shoulder'] = round(h[right_shoulder], 2)
                        result['details'].append(
                            f"Head: ${h[head]:.2f} | Shoulders: ${h[left_shoulder]:.2f} / ${h[right_shoulder]:.2f}"
                        )
                        result['details'].append(
                            f"Neckline: ${neckline:.2f} | Target: ${target:.2f}"
                        )
                        return result

        return result

    @staticmethod
    def find_double_top(high: pd.Series, low: pd.Series, close: pd.Series,
                         window: int = 60, tolerance: float = 0.03) -> Dict:
        """
        Detect Double Top pattern.
        
        Structure: Two peaks at similar level with a trough between.
        Confirmed when price breaks below the trough (support).
        """
        result = {'detected': False, 'confidence': 0, 'type': 'double_top',
                  'neckline': None, 'target': None, 'details': []}

        if len(close) < window:
            return result

        h = high.tail(window).values
        l = low.tail(window).values
        c = close.tail(window).values

        peaks = AdvancedPatternAnalyzer._find_peaks(h, order=5)
        troughs = AdvancedPatternAnalyzer._find_peaks(-l, order=5)

        if len(peaks) < 2 or len(troughs) < 1:
            return result

        for i in range(len(peaks) - 1):
            p1, p2 = peaks[i], peaks[i + 1]
            # Peaks should be at similar level
            peak_diff = abs(h[p1] - h[p2]) / max(h[p1], h[p2])
            if peak_diff < tolerance:
                # Find trough between peaks
                between_troughs = [t for t in troughs if p1 < t < p2]
                if between_troughs:
                    trough_idx = min(between_troughs, key=lambda t: l[t])
                    neckline = l[trough_idx]
                    target = neckline - (max(h[p1], h[p2]) - neckline)

                    confidence = max(0, 1.0 - peak_diff * 10)

                    if c[-1] < neckline:
                        confidence = min(confidence + 0.3, 1.0)
                        result['details'].append("✅ Neckline broken — double top confirmed")
                    else:
                        result['details'].append(f"⏳ Neckline at ${neckline:.2f} — awaiting breakout")

                    result['detected'] = True
                    result['confidence'] = round(confidence, 2)
                    result['neckline'] = round(neckline, 2)
                    result['target'] = round(target, 2)
                    result['peak_price'] = round(max(h[p1], h[p2]), 2)
                    return result

        return result

    @staticmethod
    def find_diamond_top(high: pd.Series, low: pd.Series, close: pd.Series,
                          window: int = 60) -> Dict:
        """
        Detect Diamond Top pattern.
        
        Structure: Price widens then narrows, forming a diamond shape.
        Starts with volatility expansion, then contraction.
        Typically a reversal pattern at the top of an uptrend.
        """
        result = {'detected': False, 'confidence': 0, 'type': 'diamond_top',
                  'target': None, 'details': []}

        if len(close) < window:
            return result

        h = high.tail(window).values
        l = low.tail(window).values
        c = close.tail(window).values

        # Calculate range (high - low) over time
        ranges = h - l
        mid = len(ranges) // 2

        # Diamond: ranges increase then decrease
        first_half_expanding = np.mean(ranges[:mid]) < np.mean(ranges[mid:])
        second_half_contracting = False

        # Check if second half is contracting
        if mid > 5:
            second_half_ranges = ranges[mid:]
            second_half_contracting = second_half_ranges[-1] < second_half_ranges[0] * 0.7

        # Also check for broadening then narrowing
        left_expansion = ranges[0] < ranges[mid // 2] * 1.3 if mid > 2 else False
        right_contraction = ranges[-1] < ranges[mid] * 0.7 if mid > 0 else False

        if left_expansion and right_contraction:
            confidence = 0.5
            if c[-1] < l[mid]:
                confidence = 0.8
                result['details'].append("✅ Diamond top confirmed — price broke below support")

            result['detected'] = True
            result['confidence'] = round(confidence, 2)
            result['target'] = round(l[mid] - (h.max() - l[mid]), 2)
            result['details'].append(f"Range expanded then contracted — diamond formation")

        return result

    @staticmethod
    def find_triangle(high: pd.Series, low: pd.Series, close: pd.Series,
                       window: int = 60) -> Dict:
        """
        Detect Triangle patterns (ascending, descending, symmetrical).
        
        Ascending: Flat top, rising bottom — bullish
        Descending: Falling top, flat bottom — bearish
        Symmetrical: Converging — direction depends on breakout
        """
        result = {'detected': False, 'confidence': 0, 'type': 'triangle',
                  'subtype': None, 'target': None, 'details': []}

        if len(close) < window:
            return result

        h = high.tail(window).values
        l = low.tail(window).values
        c = close.tail(window).values

        # Fit trendlines to highs and lows
        x = np.arange(len(h))
        high_slope, high_intercept = np.polyfit(x, h, 1)
        low_slope, low_intercept = np.polyfit(x, l, 1)

        # Classify triangle
        high_flat = abs(high_slope) < 0.01 * h.mean()
        low_flat = abs(low_slope) < 0.01 * l.mean()
        high_falling = high_slope < -0.01 * h.mean()
        low_rising = low_slope > 0.01 * l.mean()

        subtype = None
        if high_flat and low_rising:
            subtype = 'ascending'
        elif high_falling and low_flat:
            subtype = 'descending'
        elif high_falling and low_rising:
            subtype = 'symmetrical'

        if subtype:
            result['detected'] = True
            result['subtype'] = subtype
            result['confidence'] = 0.6

            # Calculate target from triangle height at widest point
            triangle_height = h[0] - l[0]
            if subtype == 'ascending':
                result['target'] = round(h[0] + triangle_height, 2)
                result['details'].append(f"Ascending triangle — bullish, target ${result['target']:.2f}")
            elif subtype == 'descending':
                result['target'] = round(l[0] - triangle_height, 2)
                result['details'].append(f"Descending triangle — bearish, target ${result['target']:.2f}")
            else:
                result['details'].append("Symmetrical triangle — direction depends on breakout")

            # Check for breakout
            if subtype in ('ascending', 'symmetrical') and c[-1] > h[0]:
                result['details'].append("✅ Breakout above resistance — bullish signal")
                result['confidence'] = 0.85
            elif subtype in ('descending', 'symmetrical') and c[-1] < l[0]:
                result['details'].append("✅ Breakdown below support — bearish signal")
                result['confidence'] = 0.85

        return result

    @staticmethod
    def find_wedge(high: pd.Series, low: pd.Series, close: pd.Series,
                    window: int = 60) -> Dict:
        """
        Detect Wedge patterns (rising wedge, falling wedge).
        
        Rising Wedge: Both trendlines slope up but converging — bearish
        Falling Wedge: Both trendlines slope down but converging — bullish
        """
        result = {'detected': False, 'confidence': 0, 'type': 'wedge',
                  'subtype': None, 'target': None, 'details': []}

        if len(close) < window:
            return result

        h = high.tail(window).values
        l = low.tail(window).values
        c = close.tail(window).values

        x = np.arange(len(h))
        high_slope, _ = np.polyfit(x, h, 1)
        low_slope, _ = np.polyfit(x, l, 1)

        # Both slopes positive but converging = rising wedge (bearish)
        both_up = high_slope > 0.005 * h.mean() and low_slope > 0.005 * l.mean()
        # Both slopes negative but converging = falling wedge (bullish)
        both_down = high_slope < -0.005 * h.mean() and low_slope < -0.005 * l.mean()

        # Check convergence (highs and lows getting closer)
        convergence = (h[-1] - l[-1]) < (h[0] - l[0]) * 0.6

        if both_up and convergence:
            result['detected'] = True
            result['subtype'] = 'rising_wedge'
            result['confidence'] = 0.65
            result['target'] = round(l[0], 2)
            result['details'].append("Rising wedge — bearish reversal pattern")
        elif both_down and convergence:
            result['detected'] = True
            result['subtype'] = 'falling_wedge'
            result['confidence'] = 0.65
            result['target'] = round(h[0], 2)
            result['details'].append("Falling wedge — bullish reversal pattern")

        return result

    # =========================================================================
    # GAP DETECTION
    # =========================================================================

    @staticmethod
    def find_gaps(open_series: pd.Series, high: pd.Series, low: pd.Series,
                   close: pd.Series, min_gap_pct: float = 0.5) -> List[Dict]:
        """
        Detect significant gaps (up and down).
        
        Gap Up: Today's low > Yesterday's high
        Gap Down: Today's high < Yesterday's low
        """
        gaps = []
        for i in range(1, len(close)):
            prev_high = high.iloc[i - 1]
            prev_low = low.iloc[i - 1]
            curr_open = open_series.iloc[i]
            curr_low = low.iloc[i]
            curr_high = high.iloc[i]
            curr_close = close.iloc[i]

            # Gap Up
            if curr_low > prev_high:
                gap_size = curr_low - prev_high
                gap_pct = (gap_size / prev_high) * 100
                if gap_pct >= min_gap_pct:
                    gaps.append({
                        'type': 'gap_up',
                        'date': str(close.index[i].date()) if hasattr(close.index[i], 'date') else str(close.index[i]),
                        'gap_pct': round(gap_pct, 2),
                        'gap_size': round(gap_size, 2),
                        'filled': curr_close < curr_open,  # Gap filled if price closed below open
                    })

            # Gap Down
            elif curr_high < prev_low:
                gap_size = prev_low - curr_high
                gap_pct = (gap_size / prev_low) * 100
                if gap_pct >= min_gap_pct:
                    gaps.append({
                        'type': 'gap_down',
                        'date': str(close.index[i].date()) if hasattr(close.index[i], 'date') else str(close.index[i]),
                        'gap_pct': round(gap_pct, 2),
                        'gap_size': round(gap_size, 2),
                        'filled': curr_close > curr_open,
                    })

        return gaps

    # =========================================================================
    # ADVANCED OSCILLATORS
    # =========================================================================

    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> Dict:
        """
        Commodity Channel Index (CCI).
        
        CCI = (Typical Price - SMA(TP)) / (0.015 * Mean Deviation)
        
        > +100: Overbought
        < -100: Oversold
        """
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(period).mean()
        mean_dev = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        cci_series = (tp - sma_tp) / (0.015 * mean_dev)

        current = cci_series.iloc[-1]
        return {
            'cci': round(current, 2),
            'cci_series': cci_series,
            'overbought': current > 100,
            'oversold': current < -100,
            'trend': 'RISING' if cci_series.iloc[-1] > cci_series.iloc[-5] else 'FALLING',
        }

    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict:
        """
        Williams %R.
        
        %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
        
        -20 to 0: Overbought
        -100 to -80: Oversold
        """
        hh = high.rolling(period).max()
        ll = low.rolling(period).min()
        wr = ((hh - close) / (hh - ll)) * -100

        current = wr.iloc[-1]
        return {
            'williams_r': round(current, 2),
            'overbought': current > -20,
            'oversold': current < -80,
            'trend': 'RISING' if wr.iloc[-1] > wr.iloc[-5] else 'FALLING',
        }

    @staticmethod
    def fast_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                         k_period: int = 14, d_period: int = 3) -> Dict:
        """
        Fast Stochastic Oscillator.
        
        %K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
        %D = SMA(%K, 3)
        
        > 80: Overbought
        < 20: Oversold
        """
        ll = low.rolling(k_period).min()
        hh = high.rolling(k_period).max()
        k = ((close - ll) / (hh - ll)) * 100
        d = k.rolling(d_period).mean()

        current_k = k.iloc[-1]
        current_d = d.iloc[-1]

        return {
            'fast_stoch_k': round(current_k, 2),
            'fast_stoch_d': round(current_d, 2),
            'overbought': current_k > 80,
            'oversold': current_k < 20,
            'crossover': 'BULLISH' if current_k > current_d and k.iloc[-2] <= d.iloc[-2] else
                         'BEARISH' if current_k < current_d and k.iloc[-2] >= d.iloc[-2] else 'NONE',
        }

    @staticmethod
    def kst(high: pd.Series, low: pd.Series, close: pd.Series,
             short_term: bool = True) -> Dict:
        """
        Know Sure Thing (KST) oscillator.
        
        Short-term KST uses ROC periods 10, 15, 20, 30 with MAs 10, 10, 10, 15
        Long-term KST uses ROC periods 10, 15, 20, 30 with MAs 10, 15, 20, 30
        
        KST crosses above signal line = bullish
        KST crosses below signal line = bearish
        """
        if short_term:
            roc_periods = [10, 15, 20, 30]
            ma_periods = [10, 10, 10, 15]
        else:
            roc_periods = [10, 15, 20, 30]
            ma_periods = [10, 15, 20, 30]

        weights = [1, 2, 3, 4]
        kst_values = pd.Series(0.0, index=close.index)

        for roc_p, ma_p, w in zip(roc_periods, ma_periods, weights):
            roc = close.pct_change(periods=roc_p) * 100
            roc_ma = roc.rolling(ma_p).mean()
            kst_values += roc_ma * w

        signal = kst_values.rolling(9).mean()

        current_kst = kst_values.iloc[-1]
        current_signal = signal.iloc[-1]

        return {
            'kst': round(current_kst, 4),
            'kst_signal': round(current_signal, 4),
            'kst_type': 'short_term' if short_term else 'long_term',
            'crossover': 'BULLISH' if current_kst > current_signal and kst_values.iloc[-2] <= signal.iloc[-2] else
                         'BEARISH' if current_kst < current_signal and kst_values.iloc[-2] >= signal.iloc[-2] else 'NONE',
            'trend': 'ABOVE_SIGNAL' if current_kst > current_signal else 'BELOW_SIGNAL',
        }

    @staticmethod
    def triple_ma_crossover(close: pd.Series, fast: int = 4, mid: int = 9, slow: int = 18) -> Dict:
        """
        Triple Moving Average Crossover (4-9-18 day).
        
        Bullish: Fast crosses above Mid AND Mid crosses above Slow
        Bearish: Fast crosses below Mid AND Mid crosses below Slow
        """
        sma_fast = close.rolling(fast).mean()
        sma_mid = close.rolling(mid).mean()
        sma_slow = close.rolling(slow).mean()

        # Current alignment
        fast_above_mid = sma_fast.iloc[-1] > sma_mid.iloc[-1]
        mid_above_slow = sma_mid.iloc[-1] > sma_slow.iloc[-1]
        fast_above_slow = sma_fast.iloc[-1] > sma_slow.iloc[-1]

        # Previous alignment (for crossover detection)
        prev_fast_above_mid = sma_fast.iloc[-2] > sma_mid.iloc[-2]
        prev_mid_above_slow = sma_mid.iloc[-2] > sma_slow.iloc[-2]

        # Crossover detection
        fast_cross_up = fast_above_mid and not prev_fast_above_mid
        fast_cross_down = not fast_above_mid and prev_fast_above_mid
        mid_cross_up = mid_above_slow and not prev_mid_above_slow
        mid_cross_down = not mid_above_slow and prev_mid_above_slow

        if fast_above_mid and mid_above_slow:
            signal = 'BULLISH'
        elif not fast_above_mid and not mid_above_slow:
            signal = 'BEARISH'
        else:
            signal = 'MIXED'

        return {
            'triple_ma_signal': signal,
            'fast_ma': round(sma_fast.iloc[-1], 2),
            'mid_ma': round(sma_mid.iloc[-1], 2),
            'slow_ma': round(sma_slow.iloc[-1], 2),
            'fast_cross': 'UP' if fast_cross_up else ('DOWN' if fast_cross_down else 'NONE'),
            'mid_cross': 'UP' if mid_cross_up else ('DOWN' if mid_cross_down else 'NONE'),
            'alignment': 'FULL_BULLISH' if (fast_above_mid and mid_above_slow) else
                         'FULL_BEARISH' if (not fast_above_mid and not mid_above_slow) else 'TRANSITIONING',
        }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    @staticmethod
    def _find_peaks(data: np.ndarray, order: int = 5) -> List[int]:
        """Find local maxima in a 1D array."""
        peaks = []
        for i in range(order, len(data) - order):
            if all(data[i] >= data[i - j] for j in range(1, order + 1)) and \
               all(data[i] >= data[i + j] for j in range(1, order + 1)):
                peaks.append(i)
        return peaks

    @staticmethod
    def _find_troughs(data: np.ndarray, order: int = 5) -> List[int]:
        """Find local minima in a 1D array."""
        troughs = []
        for i in range(order, len(data) - order):
            if all(data[i] <= data[i - j] for j in range(1, order + 1)) and \
               all(data[i] <= data[i + j] for j in range(1, order + 1)):
                troughs.append(i)
        return troughs

    # =========================================================================
    # MASTER ANALYSIS
    # =========================================================================

    @staticmethod
    def full_analysis(hist: pd.DataFrame) -> Dict:
        """Run all advanced pattern and indicator analysis."""
        if hist.empty or len(hist) < 60:
            return {}

        close = hist['Close']
        high = hist['High']
        low = hist['Low']
        open_s = hist['Open']
        volume = hist['Volume']

        result = {}

        # Chart patterns
        result['head_shoulders'] = AdvancedPatternAnalyzer.find_head_and_shoulders(high, low, close)
        result['double_top'] = AdvancedPatternAnalyzer.find_double_top(high, low, close)
        result['diamond_top'] = AdvancedPatternAnalyzer.find_diamond_top(high, low, close)
        result['triangle'] = AdvancedPatternAnalyzer.find_triangle(high, low, close)
        result['wedge'] = AdvancedPatternAnalyzer.find_wedge(high, low, close)

        # Gaps
        result['gaps'] = AdvancedPatternAnalyzer.find_gaps(open_s, high, low, close)
        result['recent_gaps'] = [g for g in result['gaps'] if g.get('date', '') >= str(pd.Timestamp.now().date() - pd.Timedelta(days=30))]

        # Oscillators
        result['cci'] = AdvancedPatternAnalyzer.cci(high, low, close)
        result['williams_r'] = AdvancedPatternAnalyzer.williams_r(high, low, close)
        result['fast_stochastic'] = AdvancedPatternAnalyzer.fast_stochastic(high, low, close)
        result['kst_short'] = AdvancedPatternAnalyzer.kst(high, low, close, short_term=True)
        result['kst_long'] = AdvancedPatternAnalyzer.kst(high, low, close, short_term=False)

        # Triple MA
        result['triple_ma'] = AdvancedPatternAnalyzer.triple_ma_crossover(close)

        # Summary of detected patterns
        detected_patterns = []
        for pattern_type in ['head_shoulders', 'double_top', 'diamond_top', 'triangle', 'wedge']:
            p = result.get(pattern_type, {})
            if p.get('detected'):
                detected_patterns.append({
                    'type': pattern_type,
                    'confidence': p.get('confidence', 0),
                    'details': p.get('details', []),
                })

        result['detected_patterns'] = detected_patterns
        result['pattern_summary'] = ', '.join(
            f"{p['type']} ({p['confidence']:.0%})" for p in detected_patterns
        ) if detected_patterns else 'No patterns detected'

        return result


# =========================================================================
# DEMO
# =========================================================================

if __name__ == '__main__':
    import yfinance as yf
    from investment_monitor import SymbolResolver

    resolver = SymbolResolver()

    for ticker in ['UL', 'RY', 'PZA']:
        resolved = resolver.resolve(ticker)
        print(f"\n{'=' * 80}")
        print(f"ADVANCED ANALYSIS: {ticker} ({resolved})")
        print(f"{'=' * 80}")

        try:
            stock = yf.Ticker(resolved)
            hist = stock.history(period='1y')
            if hist.index.tz:
                hist.index = hist.index.tz_localize(None)

            result = AdvancedPatternAnalyzer.full_analysis(hist)

            # Patterns
            print(f"\nPatterns: {result.get('pattern_summary', 'N/A')}")

            for ptype in ['head_shoulders', 'double_top', 'diamond_top', 'triangle', 'wedge']:
                p = result.get(ptype, {})
                if p.get('detected'):
                    print(f"\n  {ptype.upper()}:")
                    for d in p.get('details', []):
                        print(f"    {d}")

            # Gaps
            gaps = result.get('recent_gaps', [])
            if gaps:
                print(f"\nRecent Gaps:")
                for g in gaps[-5:]:
                    filled = "FILLED" if g.get('filled') else "OPEN"
                    print(f"  {g['date']}: {g['type']} {g['gap_pct']:.2f}% ({filled})")

            # Oscillators
            cci = result.get('cci', {})
            wr = result.get('williams_r', {})
            fstoch = result.get('fast_stochastic', {})
            kst = result.get('kst_short', {})
            tma = result.get('triple_ma', {})

            print(f"\nOscillators:")
            print(f"  CCI: {cci.get('cci', 'N/A')} ({'OB' if cci.get('overbought') else 'OS' if cci.get('oversold') else 'neutral'})")
            print(f"  Williams %R: {wr.get('williams_r', 'N/A')} ({'OB' if wr.get('overbought') else 'OS' if wr.get('oversold') else 'neutral'})")
            print(f"  Fast Stoch: K={fstoch.get('fast_stoch_k', 'N/A')} D={fstoch.get('fast_stoch_d', 'N/A')} cross={fstoch.get('crossover', 'N/A')}")
            print(f"  KST (short): {kst.get('kst', 'N/A')} signal={kst.get('kst_signal', 'N/A')} {kst.get('crossover', 'N/A')}")
            print(f"  Triple MA (4-9-18): {tma.get('triple_ma_signal', 'N/A')} align={tma.get('alignment', 'N/A')}")

        except Exception as e:
            print(f"Error: {e}")

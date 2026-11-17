# TA-Lib wrapper patterns & gotchas (investment-agent SRP extraction)

Condensed, session-tested knowledge for wrapping TA-Lib as SRP indicators during
the `investment-agent` Phase 3 refactor. Companion to the SKILL.md "Phase 3 SRP/DI
+ TA-Lib recipe".

## Thin-wrapper convention (canonical)
Each SRP calculator takes a price-history `pd.DataFrame` (cols `Open/High/Low/Close/
Volume`) and calls TA-Lib; it returns a plain dict. TA-Lib is the calculation engine
— pandas only where TA-Lib has no primitive (price change, realized vol,
support/resistance). `TechnicalAnalysisService` composes the 9 monster-compat
calculators; `TASuite` composes those + every expanded wrapper so "apply all the
calculations to our data" is one `analyze(df)` call.

## Before wrapping: probe TA-Lib availability at runtime
The Python binding is NOT a 1:1 mirror of the C library. Verify before relying on a
function (don't assume `talib.<X>` exists):

```python
import talib
names = ["EMV","AROON","HT_PHASOR","HT_SINE","ADX","MFI","ULTOSC", ...]
missing = [n for n in names if not hasattr(talib, n)]
print("MISSING:", missing)   # EMV is missing in 0.7.0
```

Confirm tuple-returning shapes too (these return 2-tuples — unpack carefully):
```python
up, down = talib.AROON(h, l, timeperiod=14)          # (aroonup, aroondown)
ph = talib.HT_PHASOR(c); inphase, quad = ph[0], ph[1]
sine = talib.HT_SINE(c); s, lead = sine[0], sine[1]
```

## Binding gaps observed (0.7.0)
- `talib.EMV` does NOT exist → omit Ease-of-Movement (or hand-roll in a separate
  module; don't fake a TA-Lib wrapper for it).
- `BETA`/`CORREL` need a paired series (benchmark) → omit from the single-symbol
  applied-TA set unless you pass a market series in.

## Candlestick patterns: EXCLUDED (project finding)
`talib.CDL*` patterns are deliberately NOT in `TASuite`. Prior experiments on this
dataset found the CDL signals to be *contra-wins* — they predicted the opposite of
subsequent price action. Encode the exclusion so it can't be silently re-added:
```python
EXCLUDED_FROM_APPLY_ALL = "TA-Lib CDL* candlestick patterns (contra-wins)"
# test:
cdl = [k for k in out if k.lower().startswith("cdl")]
assert cdl == []
```
(Also saved to memory so a future session doesn't re-add them.)

## Test flip when moving an SRP from pandas → TA-Lib
A pre-existing test that asserts `srp[k] == pytest.approx(monster[k])` will FAIL
once the calculator uses TA-Lib (Wilder RSI, EMA-based MACD differ from legacy
pandas). Fix: keep ONLY the key-set assertion (`set(monster.keys()) == set(srp.keys())`,
40 keys for the monster-compat service) and rename the test `*_keys_match_*`.
Values legitimately diverge — that is the intended upgrade, but live signal values
WILL shift, so flag it when the monster is rewired.

## Defensive suite composition
`TASuite.analyze` should `try/except` around each calculator so one unavailable or
erroring indicator (e.g. insufficient history) doesn't sink the whole dict. Return
scalars (float/int/str) or None — never leak raw TA-Lib arrays into the result.

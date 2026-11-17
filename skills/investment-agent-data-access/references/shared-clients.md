# Shared clients & helpers (investment-agent)

Exact signatures for the standardized classes. Route ALL new I/O through these.

## HttpClient — `src/common/http_client.py`
```python
from src.common.http_client import HttpClient
http = HttpClient(timeout=15, retries=3, backoff=0.5)
resp = http.get(url, params=None, headers=None)        # requests.Response
resp = http.post(url, json=None, data=None, headers=None)
```
- Wraps `requests.Session`; retries with exponential backoff; raises on exhaustion.
- Allowlisted in the guard for `requests` usage.

## LLMClient — `src/common/llm_client.py`
```python
from src.common.llm_client import LLMClient
llm = LLMClient(default_model="gpt-4o-mini")   # reads OPENAI_API_KEY / USE_OLLAMA_FALLBACK / OLLAMA_MODEL from env
text = llm.complete(prompt, model=None, max_tokens=300)   # str, '' on total failure
```
- OpenAI → Ollama (`http://localhost:11434/api/generate`) → returns `''` if both fail.
- Caller keeps its own template fallback for the `''` case.
- Allowlisted in the guard for `requests` + `import openai` / `OpenAI(`.

## WebhookDispatcher — `src/delivery/webhook_dispatcher.py`
```python
from src.delivery.webhook_dispatcher import WebhookDispatcher
WebhookDispatcher(urls=[DISCORD_WEBHOOK_URL]).send_raw({"content": content})
# or with embeds:
WebhookDispatcher([webhook_url]).send_raw({"embeds": [embed]})
```
- Constructor: `WebhookDispatcher(urls: List[str] = None, timeout: int = None)`.
  **NOT** `webhook_urls=` — that kwarg does not exist on this class (Pyright error).
- `send_raw(obj: Dict, content_type='application/json')` POSTs `obj` JSON to every URL.
- Uses `urllib.request` internally (allowlisted).

## indicator_math — `src/indicators/indicator_math.py`
```python
from src.indicators.indicator_math import calculate_rsi, calculate_natr
rsi  = calculate_rsi(close: pd.Series, n=14) -> pd.Series
natr = calculate_natr(high, low, close: pd.Series, n=14) -> pd.Series
```
- Canonical RSI/NATR. Returns `pd.Series` (callers use `.iloc[-1]`). Do NOT re-implement.

## detect_volume_spike — `src/analysis/volume_spike.py`
```python
from src.analysis.volume_spike import detect_volume_spike
result = detect_volume_spike(symbol, threshold=3.0)   # dict | None
```
- Returns the rich alert dict (`volume_ratio`, `today_volume`, `avg_volume`,
  `current_price`, `price_change_pct`, `alert`, ...) or `None` on no-data/error.
- `result['alert']` is `vol_ratio >= threshold`. Volume-spike CHECKERS that only want
  "is there a spike?" should return `result if (result and result.get('alert')) else None`
  so they don't emit alerts for non-spikes.
- Built on `YFinanceFetcher`; never calls `yfinance` directly.

## to_ohlcv_dataframe — `src/db/stock_price_dto.py`
```python
from src.db.stock_price_dto import to_ohlcv_dataframe
df = to_ohlcv_dataframe(dtos)   # index=Date, cols Open/High/Low/Close/Volume/Adj Close
```
- Canonical DTO→OHLCV DataFrame converter. Reuse instead of re-writing the loop.

## YFinanceFetcher.fetch_daily gotcha
```python
fetcher = YFinanceFetcher(period='30d', interval='1d')
dtos = fetcher.fetch_daily([symbol], lookback_days=5, period='30d')
```
- Pass `period=` to `fetch_daily`; the constructor's `self.period` is IGNORED inside
  the method (it falls back to `_lookback_to_period(lookback_days)` unless you pass
  `period=`). For exact windows (e.g. '30d') always pass `period=` to the call.

## Guard cheat-sheet
| Command | Mode | Fails on violation? |
|---------|------|---------------------|
| `python3 scripts/guard_standardized_access.py` | full-repo audit | No (warnings only, exit 0) |
| `... --staged` | pre-commit (staged files) | Yes (exit 1) |
| `... --changed` | CI diff vs origin/main | Yes (exit 1) |
| `... --full` | ⚠️ NOT A VALID FLAG | argparse exits 2 (looks like 0 violations) |

- Edit `BLOCK_RULES`/`WARN_RULES` + `ALLOW_*` lists in `scripts/guard_standardized_access.py`.
- Every BLOCK regex needs **balanced parens** — `\.history\(` (good) vs `\.history\((`
  (crashes: `re.error: missing ), unterminated subpattern`).

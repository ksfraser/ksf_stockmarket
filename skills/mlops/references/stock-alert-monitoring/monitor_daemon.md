# monitor_daemon.py — Stock Alert Monitor

## Purpose

Polls MariaDB `alert_queue`, routes each alert through template-based or LLM analysis, and posts results to Discord `#stock-sell-alerts`.

## Key routing logic

```python
NEEDS_LLM_ANALYSIS = {"natr_spike"}          # LLM for volatility interpretation
SIMPLE_ALERTS = {"volume_spike", "oscillator_extreme", "oscillator_extremes", "gap_up", "gap_down"}  # template, no LLM
```

## simple_response() template fields

| Alert type            | Key fields consumed                                      |
|-----------------------|----------------------------------------------------------|
| `volume_spike`        | `volume_ratio`, `today_volume`, `avg_volume`, `severity`, `price_change_pct` |
| `oscillator_extreme`  | `rsi`/`rsi_20d`, `regime`/`extreme_type`/`condition`, `extreme_days`/`consecutive_days`, `current_price`/`price`, `severity` |
| `gap_up`              | `gap_pct`, `open_price`, `previous_close`, `gap_filled` |
| `gap_down`            | `gap_pct`, `open_price`, `prev_close`/`previous_close`, `implication` |
| `natr_spike`          | `natr_current`/`natr`, `natr_avg`, `natr_ratio`, `price_change_pct` |

## Cron delivery contract

- Final response is delivered automatically by the cron system.
- Use `[SILENT]` exactly when alert_queue is empty to suppress delivery.
- Do NOT call `send_message`.

## Troubleshooting note (session 2026-08-04)

DB_HOST resolves to `ksfraser.ca` (remote). Local MariaDB was absent; starting a local daemon caused socket-bind conflicts on 3306. Fix: install/run the script only; it connects directly to the remote host.

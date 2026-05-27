# Stock Data API — Architecture Design

## Problem Statement

Two systems need access to the same stock/ETF data:
1. **Python analysis engine** — backtesting, screening, TA, daily monitoring
2. **FA module (PHP)** — portfolio display, transfer tracking, revaluation

Currently the Python scripts write directly to `analysis_results.db` (SQLite) and the FA module would need its own DB connection. This creates:
- Data duplication
- Sync issues
- No single source of truth
- The 4GB mysqldump problem Kevin experienced (monolithic DB backup)

## Proposed Architecture: Dedicated Stock Data API

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Stock Data API                                │
│                    (Python FastAPI, :8080)                           │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ /prices/*     │  │ /symbols/*   │  │ /portfolio/*             │  │
│  │ GET prices    │  │ GET info     │  │ GET/POST holdings        │  │
│  │ GET history   │  │ GET search   │  │ GET/POST transactions    │  │
│  │ POST refresh  │  │ GET validate │  │ GET summary              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ /analysis/*   │  │ /screens/*   │  │ /backtest/*              │  │
│  │ GET signals   │  │ POST run     │  │ POST run                 │  │
│  │ GET indicators│  │ GET results  │  │ GET status               │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    MariaDB (stock_data DB)                     │   │
│  │  • prices (symbol, date, open, high, low, close, volume)     │   │
│  │  • symbols (symbol, name, exchange, currency, type, sector)  │   │
│  │  • holdings (user, symbol, shares, cost_basis, account)      │   │
│  │  • transactions (user, symbol, type, shares, price, date)    │   │
│  │  • dividends (symbol, ex_date, amount, currency)             │   │
│  │  • watchlists (user_id, name, symbols[])                     │   │
│  │  • backtest_runs, backtest_trades                            │   │
│  │  • data_import_log                                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              yfinance / CSV (data sources)                    │   │
│  │  • yfinance for live prices and symbol info                  │   │
│  │  • CSV import for historical bulk data                       │   │
│  │  • SymbolResolver for TSX/NYSE disambiguation                │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │                                          │
          │ HTTP/JSON                                │ HTTP/JSON
          │                                          │
          ▼                                          ▼
┌─────────────────────┐                  ┌─────────────────────────┐
│  Python CLI Scripts  │                  │  FA Module (PHP)        │
│  (analysis engine)   │                  │  ksf_FA_StockMarket     │
│                      │                  │                         │
│  • daily_monitor     │                  │  • Portfolio display    │
│  • backtest_engine   │                  │  • Transfer tracking    │
│  • screener          │                  │  • Revaluation          │
│  • price_alerts      │                  │  • Holdings CRUD        │
└─────────────────────┘                  └─────────────────────────┘
```

## Key Design Decisions

### 1. Separate Database from FA
The stock data lives in its **own MariaDB database** (`stock_data`), completely separate from FA's database (`ksf_fa`). 

**Why:**
- FA's DB stays lean — only FA tables (GL, AP, AR, inventory, etc.)
- Stock data can be backed up independently (solves the 4GB dump problem)
- FA module reads stock data via API, not direct DB access
- If the stock data DB crashes, FA keeps running

### 2. API-Based Access (Not Direct DB)
Both Python and PHP talk to the API, not the database directly.

**Why:**
- Single source of truth for business logic (e.g., symbol resolution)
- Rate limiting and caching at the API level
- Can swap the DB engine without changing clients
- Authentication/authorization in one place
- The 2000+ symbols of price data stay in one managed pipeline

### 3. Database Backup Strategy (Lessons from 2013)
Kevin's 2013 crash: single mysqldump file >4GB caused filesystem truncation.

**Solution:**
- **Per-table dumps** — shell script iterates tables, dumps each separately
- **Price data partitioned by year** — old years are read-only, backed up once
- **Incremental backups** — only new/changed records since last dump
- **Separate backup schedules:**
  - `symbols`, `holdings`, `transactions`: daily (small, critical)
  - `prices`: weekly (large, append-only)
  - `backtest_*`: monthly (can be regenerated)

```bash
#!/bin/bash
# backup_stock_data.sh — per-table backup with rotation
DB="stock_data"
BACKUP_DIR="/backup/stock_data/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Get table list
tables=$(mysql -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='$DB'")

for table in $tables; do
    # Skip if table is empty
    count=$(mysql -N -e "SELECT COUNT(*) FROM $DB.$table")
    if [ "$count" -eq 0 ]; then continue; fi
    
    # Dump with compression
    mysqldump --single-transaction "$DB" "$table" | gzip > "$BACKUP_DIR/${table}.sql.gz"
    echo "Backed up $table ($count rows)"
done

# Keep only last 30 days
find /backup/stock_data -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;
```

### 4. Symbol Resolution (TSX/NYSE)
The API handles symbol resolution centrally — clients send `MICC` and get back the correct Yahoo Finance ticker. No more per-script `KNOWN_US` sets.

```json
// GET /symbols/resolve/MICC
{
    "input": "MICC",
    "resolved": "MICC",
    "exchange": "NYQ",
    "currency": "USD",
    "name": "The Magnum Ice Cream Company N.V.",
    "type": "EQUITY"
}

// GET /symbols/resolve/CM
{
    "input": "CM",
    "resolved": "CM.TO",
    "exchange": "TOR",
    "currency": "CAD",
    "name": "Canadian Imperial Bank of Commerce",
    "type": "EQUITY"
}
```

### 5. PHP Client (FA Module Side)
The FA module uses a simple PHP HTTP client to talk to the API:

```php
// src/Service/StockDataApi.php
class StockDataApi {
    private string $baseUrl;
    
    public function __construct() {
        $this->baseUrl = $_ENV['STOCK_API_URL'] ?? 'http://127.0.0.1:8080';
    }
    
    public function getPrice(string $symbol): ?array {
        $response = file_get_contents("{$this->baseUrl}/prices/{$symbol}/current");
        return json_decode($response, true);
    }
    
    public function getHolding(string $user, string $symbol): ?array {
        $response = file_get_contents(
            "{$this->baseUrl}/portfolio/{$user}/holdings/{$symbol}"
        );
        return json_decode($response, true);
    }
    
    // ... etc
}
```

## API Endpoints (Draft)

### Prices
| Method | Path | Description |
|--------|------|-------------|
| GET | `/prices/{symbol}/current` | Latest price + metadata |
| GET | `/prices/{symbol}/history?from=&to=&interval=` | OHLCV history |
| POST | `/prices/refresh` | Trigger yfinance refresh for symbols |
| GET | `/prices/batch?symbols=CM,CNR,BPF.UN` | Batch price fetch |

### Symbols
| Method | Path | Description |
|--------|------|-------------|
| GET | `/symbols/resolve/{symbol}` | Resolve TSX/NYSE ambiguity |
| GET | `/symbols/{symbol}` | Full symbol metadata |
| GET | `/symbols/search?q=` | Search by name/symbol |
| GET | `/symbols/validate/{symbol}` | Check if symbol exists |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/portfolio/{user}/holdings` | All holdings for user |
| GET | `/portfolio/{user}/holdings/{symbol}` | Single holding |
| POST | `/portfolio/{user}/holdings` | Add/update holding |
| DELETE | `/portfolio/{user}/holdings/{symbol}` | Remove holding |
| GET | `/portfolio/{user}/summary` | Total value, P&L, allocation |
| GET | `/portfolio/{user}/transactions` | Transaction history |
| POST | `/portfolio/{user}/transactions` | Record transaction |

### Analysis
| Method | Path | Description |
|--------|------|-------------|
| GET | `/analysis/{symbol}/signal` | Current TA signal |
| GET | `/analysis/{symbol}/indicators` | Full indicator set |
| POST | `/screens/run` | Run a screen |
| GET | `/screens/{id}/results` | Screen results |

### Backtest
| Method | Path | Description |
|--------|------|-------------|
| POST | `/backtest/run` | Submit backtest job |
| GET | `/backtest/{id}/status` | Job status |
| GET | `/backtest/{id}/results` | Full results + trade log |

## Migration Path

### Phase A: API Skeleton + Symbol Resolution
1. Create FastAPI app with `/symbols/resolve` endpoint
2. Port SymbolResolver from investment_monitor.py
3. Move KNOWN_US/KNOWN_TSX lists to DB table (editable via API)
4. Test with the 5 previously-broken symbols

### Phase B: Price Data Pipeline
1. Create `prices` and `symbols` tables in MariaDB
2. Build yfinance ingestion service
3. Import existing CSV data (1997 files → API bulk import)
4. Replace direct yfinance calls in Python scripts with API calls

### C: Portfolio + FA Integration
1. Create `holdings`, `transactions`, `dividends` tables
2. Build PHP API client for FA module
3. FA module reads holdings/transactions via API
4. FA module writes transfers/revaluations via API
5. Python backtest reads portfolio via API

### D: Analysis Engine
1. Port TA, screening, backtesting to API endpoints
2. Daily monitor calls API instead of direct DB
3. Queue system for long-running backtests

## Benefits

1. **Solves the backup problem** — per-table dumps, partitioned price data
2. **Single symbol resolver** — no more per-script KNOWN_US lists
3. **FA stays clean** — stock data in separate DB, accessed via API
4. **Python scripts simplify** — no direct DB access, just API calls
5. **Extensible** — new clients (mobile app, Discord bot, etc.) just call the API
6. **Testable** — API can be tested independently of FA or Python
7. **Scalable** — can add caching (Redis), rate limiting, auth later

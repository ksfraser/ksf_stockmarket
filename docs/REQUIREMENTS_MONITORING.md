# Monitoring & Automation Requirements
## ksf_stockmarket System Integration

> **Version:** 1.0 | **Date:** 2026-06-07 | **Status:** Draft

---

## 1. Goal

Migrate monitoring cron jobs from Hermes orchestration to standalone system cron with containerized deployment via Ansible, removing LLM dependency from non-business-critical monitoring tasks.

---

## 2. Current State Analysis

### 2.1 Hermes Cron Jobs (19 active)

| Job | Script | Schedule | LLM Required? | Business Critical? |
|-----|--------|----------|---------------|------------------|
| Daily Monitor | daily_monitor_standalone.py | 7:30 AM weekdays | No | ✅ Yes (must not modify) |
| Stop Loss | watchlist_stop_loss.py | 8:00 AM weekdays | No | ✅ Yes (must not modify) |
| Price Alert | price_alert_check.py | 9 AM-4 PM weekdays | No | ✅ Yes (must not modify) |
| Volume Spike | volume_spike_check.py | Every 30 min | No | No |
| Delisted Check | check_delisted.py | Weekly | No | No |
| Price Sync | price_sync.py | Hourly | No | No |
| ... | ... | ... | ... | ... |

### 2.2 DRY Violations Identified

1. **Symbol Resolution Duplication** — ✅ RESOLVED
   - Was: `volume_spike_check.py`, `price_alert_check.py` had inline `.UN` / fallback logic
   - Now: Canonical resolver lives at:
     - Python: `python/src/symbol_resolver.py` (`resolve_for_yfinance()`)
     - PHP: `php/src/Util/SymbolResolver.php` (`SymbolResolver::resolve()`)
   - All yfinance callers now route through the resolver (see FR-01 enforcement below)

2. **Database Connection Duplication**
   - Each script has hardcoded MySQL credentials
   - **Solution**: Create shared `database.py` module with environment variable config

3. **yfinance Usage Duplication**
   - Every script creates its own `yf.Ticker()` calls
   - **Solution**: Create shared `price_fetcher.py` with caching

4. **Notification Duplication**
   - Email/Discord notification logic scattered
   - **Solution**: Centralize in `notification.py`

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-01: Shared Resolver Mandatory
All monitoring scripts must use the canonical resolver for ticker formatting.
- Python: `python/src/symbol_resolver.py` — `resolve_for_yfinance(symbol)`
- PHP: `php/src/Util/SymbolResolver.php` — `SymbolResolver::resolve($symbol)`
No script may call `yf.Ticker(symbol)` or `yf.download(symbol)` directly with an unresolved DB symbol.

#### FR-02: Centralized Price Fetching
All monitoring scripts must use shared price fetchers with caching rather than creating `yf.Ticker()` per-script.

```sql
-- Volume snapshots for intraday monitoring
CREATE TABLE IF NOT EXISTS volume_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    price DECIMAL(12,4),
    volume BIGINT,
    volume_5d_avg BIGINT,
    volume_ratio DECIMAL(6,2),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_date (symbol, date),
    INDEX idx_volume_ratio (volume_ratio DESC)
);

-- Price alerts (migration from SQLite)
CREATE TABLE IF NOT EXISTS price_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    alert_type ENUM('BELOW', 'ABOVE', 'TRAILING_STOP') NOT NULL,
    threshold_value DECIMAL(12,4),
    trailing_stop_price DECIMAL(12,4),
    trailing_limit_price DECIMAL(12,4),
    active BOOLEAN DEFAULT 1,
    triggered_count INT DEFAULT 0,
    last_triggered TIMESTAMP NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_active (active),
    INDEX idx_ticker (ticker)
);

-- Symbol status tracking (migration from SQLite)
CREATE TABLE IF NOT EXISTS symbol_status (
    symbol VARCHAR(20) PRIMARY KEY,
    resolved_symbol VARCHAR(20),
    status ENUM('active', 'delisted', 'renamed', 'exchange_changed', 'error') DEFAULT 'active',
    name VARCHAR(255),
    exchange VARCHAR(50),
    currency CHAR(3),
    last_price DECIMAL(12,4),
    last_check_date DATE,
    first_delisted_date DATE NULL,
    error_message TEXT,
    consecutive_failures INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status)
);

-- Monitoring run logs
CREATE TABLE IF NOT EXISTS monitoring_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_name VARCHAR(50) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    status ENUM('success', 'error', 'no_data') NOT NULL,
    symbol_count INT,
    alert_count INT,
    details JSON,
    INDEX idx_job (job_name, started_at)
);
```

#### FR-03: Ansible Role for ksf_stockmarket

```yaml
# ksf_stockmarket role structure
ksf_stockmarket/
├── tasks/
│   ├── main.yml          # Main entry point
│   ├── install_packages.yml  # Required packages
│   ├── configure_database.yml  # MariaDB setup
│   ├── deploy_containers.yml   # Podman pod deployment
│   └── configure_cron.yml      # System cron setup
├── vars/
│   └── main.yml          # Default variables
├── templates/
│   ├── .env.j2           # Environment file with vault secrets
│   ├── podman-compose.yml.j2  # Container definitions
│   └── crontab.j2        # System crontab
├── files/
│   └── python-requirements.txt
└── defaults/
    └── main.yml          # Override defaults
```

#### FR-04: Container Pod Architecture

```
Pod: ksf_stockmarket
├── Container: mariadb
│   - Port: 3306 (internal)
│   - Volume: /var/lib/mysql
│   - Database: ksfraser_stock_market
│
├── Container: webserver (nginx + php-fpm)
│   - Port: 80/443 (external)
│   - Volume: /var/www/stockmarket-app
│   - Depends on: mariadb
│
└── Container: python-monitor
    - Image: python:3.10-slim (or custom)
    - Runs monitoring scripts
    - Shares network with webserver
    - Volume: /var/www/stockmarket-app/python:/app
```

#### FR-05: Firewall Rules

```bash
# HTTP/HTTPS access
firewall-cmd --add-service=http --permanent
firewall-cmd --add-service=https --permanent

# SSH (always allow)
firewall-cmd --add-service=ssh --permanent

# MariaDB access (if remote)
# firewall-cmd --add-port=3306/tcp --permanent

# Podman API (if needed)
# firewall-cmd --add-port=8080/tcp --permanent

# Reload firewall
firewall-cmd --reload
```

### 3.2 Non-Functional Requirements

#### NFR-01: Security
- All secrets stored in Ansible Vault
- Database credentials injected via `.env` file
- No hardcoded passwords in code

#### NFR-02: Idempotency
- Ansible role must be idempotent (safe to re-run)
- Container restart should preserve data

#### NFR-03: Monitoring
- All runs logged to `monitoring_runs` table
- Error output captured and logged
- Health check endpoint for container status

#### NFR-04: Backup
- MariaDB data backed up daily
- Python scripts backed up via git

---

## 4. Use Cases

### UC-01: Volume Spike Monitoring
```
Actor: System Cron
Precondition: Symbol in watchlist_symbols with monitor_volume=1
Trigger: Every 30 minutes during market hours
Main Success Scenario:
  1. Fetch all monitored symbols from MariaDB
  2. Get current price and volume from yfinance
  3. Calculate 5-day average volume
  4. If volume_ratio >= threshold, log alert
  5. Update volume_snapshots table
Postcondition: Alert logged, snapshot stored
```

### UC-02: Price Alert Check
```
Actor: System Cron
Precondition: Active price alerts in database
Trigger: Every 15 minutes during market hours
Main Success Scenario:
  1. Fetch all active price alerts
  2. Get current prices
  3. If price triggers condition, send notification
  4. Log trigger to price_alerts table
Postcondition: Triggered alerts sent
```

### UC-03: Delisted Symbol Detection
```
Actor: System Cron
Precondition: Known symbols in database
Trigger: Weekly (Sunday night)
Main Success Scenario:
  1. Fetch all known symbols
  2. Check each against yfinance
  3. Update symbol_status table
  4. Log results to monitoring_runs
Postcondition: Symbol status updated
```

---

## 5. Test Cases

### TC-01: Volume Spike Detection
```bash
# Setup: Add test symbol to watchlist_symbols
# Input: Volume spike threshold 2.0
# Expected: Alert when today_volume > 2x avg_volume
# Verification: Check volume_snapshots table, verify alert logged
```

### TC-02: Price Alert Trigger
```bash
# Setup: Add price alert for symbol with low threshold
# Input: Current price below threshold
# Expected: Alert triggered, notification sent
# Verification: Check price_alerts.triggered_count incremented
```

### TC-03: Containerization
```bash
# Setup: Run Ansible role on clean system
# Input: Install ksf_stockmarket role
# Expected: All containers running, database accessible
# Verification: curl http://localhost returns dashboard
```

### TC-04: DRY Compliance
```bash
# Verify: All scripts import from shared modules
# Verify: No hardcoded credentials in Python files
# Verify: Symbol resolution uses centralized module
```

---

## 6. UAT Scripts

Create executable test scripts in `/scripts/uat/`:

```bash
#!/bin/bash
# test_volume_spike.sh
set -e
export DB_HOST=localhost
python3 /app/src/monitoring/volume_spike_check.py --json > /tmp/result.json
python3 -c "
import json
r = json.load(open('/tmp/result.json'))
assert 'n_checked' in r
assert isinstance(r['n_spikes'], int)
print('PASS: Volume spike check returns valid JSON')
"
```

---

## 7. Inventory Variables

Add to `/etc/ansible/hosts`:

```yaml
[stockmarket_app]
localhost ansible_connection=local

[stockmarket_app:vars]
# Git source
stockmarket_git_repo: "https://github.com/ksfraser/ksf_stockmarket"
stockmarket_git_branch: "main"

# Database
mariadb_root_password: "{{ vault_mariadb_root_password }}"
stockmarket_db_name: "ksfraser_stock_market"
stockmarket_db_user: "ksfraser_stockmarket"
stockmarket_db_password: "{{ vault_stockmarket_db_password }}"

# Application
app_timezone: "America/Toronto"
app_market_open: "09:30"
app_market_close: "16:00"

# Monitoring enabled flags
enable_volume_monitoring: true
enable_price_alerts: true
enable_delisted_check: true
enable_price_sync: true

# Notification settings
smtp_host: "localhost"
smtp_from: "alerts@ksfraser.ca"
alert_recipients: "fraser.ks@gmail.com"
```

---

## 8. Migration Phases

### Phase 1: Requirements & Architecture (THIS DOCUMENT)
- Document requirements ✅
- Create test cases ✅
- Define Ansible role structure

### Phase 2: Shared Modules
- Create `database.py` with env var config
- Create `symbol_resolver.py`
- Create `price_fetcher.py`
- Create `notification.py`

### Phase 3: Script Refactoring
- Refactor `volume_spike_check.py` to use shared modules
- Refactor `check_delisted.py` to use shared modules
- Update database connections to MariaDB

### Phase 4: Ansible Role
- Create `ksf_stockmarket` role
- Create podman-compose.yml
- Configure firewall rules
- Setup system cron

### Phase 5: Testing
- Run UAT scripts
- Verify containerized deployment
- Test database migrations

### Phase 6: Deployment
- Deploy to production
- Monitor for 1 week
- Remove old Hermes cron jobs (non-business critical only)

---

## 9. Open Questions

1. Should we use Podman pods or Docker Compose?
2. Do we need a separate Python container or can it run in webserver?
3. Should MariaDB be in-container or external?
4. How to handle credential rotation for vault-stored secrets?
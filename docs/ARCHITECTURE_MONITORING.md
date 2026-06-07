# Architecture Specification
## Containerized Monitoring System

> **Version:** 1.0 | **Date:** 2026-06-07

---

## 1. Overview

This document specifies the architecture for migrating monitoring jobs to a containerized deployment using Podman with Ansible orchestration.

---

## 2. Container Architecture

### 2.1 Pod Structure

```
Pod: ksf_stockmarket_monitoring
│
├── mariadb-server (service inside pod)
│   ├── Ports: 3306 (internal only)
│   ├── Volume: /var/lib/mysql → /var/lib/containers/storage/volumes/mariadb-data
│   ├── Environment: Loaded from .env via Ansible Vault
│   └── Init: Executes schema.sql on first run
│
├── nginx-php-fpm (service inside pod)
│   ├── Ports: 80 → 8080 (external HTTP)
│   ├── Volume: ./php → /var/www/html (code)
│   └── Depends: mariadb-server
│
└── python-monitor (service inside pod)
    ├── Command: cron daemon (runs scripts on schedule)
    ├── Volume: ./python/src → /app/src
    └── Shares: Network namespace with pod
```

### 2.2 Network Configuration

```yaml
Network: ksf_stockmarket_network
Driver: bridge
Subnet: 172.20.20.0/24
Gateway: 172.20.20.1

Services expose:
- Nginx: 8080 (external mapping)
- MariaDB: 3306 (pod-internal only)
- Python Monitor: No ports (cron-driven)
```

---

## 3. Ansible Role Structure

```yaml
/root/.ansible/roles/ksf_stockmarket/
├── defaults/
│   └── main.yml           # Default variables, safe to override
│
├── vars/
│   └── main.yml           # Role-specific variables (not overridden)
│
├── tasks/
│   ├── main.yml           # Entry point, includes others
│   ├── install_packages.yml    # Podman, nginx, php, python deps
│   ├── configure_firewall.yml  # Open HTTP/HTTPS ports
│   ├── deploy_pod.yml         # Podman pod creation
│   ├── configure_database.yml   # MariaDB user/table setup
│   └── configure_cron.yml     # System cron for non-container jobs
│
├── templates/
│   ├── .env.j2            # Environment file (vault credentials)
│   ├── podman-compose.yml.j2  # Pod definition
│   ├── crontab.j2           # System crontab for monitoring jobs
│   └── mariadb.cnf.j2         # Custom MariaDB config
│
├── files/
│   ├── python-requirements.txt  # Python dependencies
│   └── schema-monitoring.sql      # Monitoring tables schema
│
├── handlers/
│   └── main.yml           # Restart services on config change
│
└── meta/
    └── main.yml           # Role dependencies (ksf.firewall, ksf.podman)
```

---

## 4. File Changes

### 4.1 New Files to Create

| Path | Purpose |
|------|---------|
| `/root/.ansible/roles/ksf_stockmarket/tasks/*.yml` | Role tasks |
| `/root/.ansible/roles/ksf_stockmarket/templates/*.j2` | Templates |
| `/root/.ansible/roles/ksf_stockmarket/files/*.txt` | Requirements |
| `/home/ksf_stockmarket/ksf_stockmarket/python/src/database.py` | Shared DB module |
| `/home/ksf_stockmarket/ksf_stockmarket/python/src/symbol_resolver.py` | Shared symbol module |
| `/home/ksf_stockmarket/ksf_stockmarket/python/src/price_fetcher.py` | Shared price module |
| `/home/ksf_stockmarket/ksf_stockmarket/python/src/monitoring/volume_spike.py` | Refactored script |
| `/home/ksf_stockmarket/ksf_stockmarket/python/src/monitoring/delisted_check.py` | Refactored script |

### 4.2 Modified Files

| Path | Changes |
|------|---------|
| `/home/ksf_stockmarket/ksf_stockmarket/python/db_connector.py` | Add MariaDB connection support |
| `/etc/ansible/hosts` | Add inventory group and variables |
| `/root/.ansible/roles/ksf.mariadb/*` | May need updates for stockmarket user |

---

## 5. Database Schema

### 5.1 New Tables

```sql
-- Monitoring run history
CREATE TABLE IF NOT EXISTS monitoring_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_name VARCHAR(50) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    status ENUM('success', 'error', 'no_data') NOT NULL,
    symbol_count INT,
    alert_count INT,
    details JSON,
    INDEX idx_job_time (job_name, started_at)
);

-- Volume snapshots
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
    INDEX idx_ratio (volume_ratio DESC)
);
```

### 5.2 Migration from SQLite

Tables to migrate from `/root/.hermes/cache/analysis_results.db`:
- `symbol_status` → Already has MariaDB compatible schema
- `price_alerts` → Already defined above

---

## 6. Cron Schedule

### 6.1 System Cron (migrated from Hermes)

```cron
# /etc/cron.d/stockmarket-monitoring
# Volume spike check - every 30 min during market hours
*/30 9-16 * * 1-5 www-data /opt/stockmarket/bin/volume_spike_check.py --json >> /var/log/stockmarket-volume.log 2>&1

# Price alerts - every 15 min during market hours  
*/15 9-16 * * 1-5 www-data /opt/stockmarket/bin/price_alert_check.py >> /var/log/stockmarket-alerts.log 2>&1

# Delisted symbols - weekly Sunday night
0 2 * * 0 www-data /opt/stockmarket/bin/check_delisted.py --weekly >> /var/log/stockmarket-delisted.log 2>&1

# Price sync - hourly
0 * * * 1-5 www-data /opt/stockmarket/bin/price_sync.py >> /var/log/stockmarket-sync.log 2>&1
```

---

## 7. Security Model

### 7.1 Ansible Vault

```yaml
# /root/.ansible/vault/stockmarket-secrets.yml
stockmarket_db_root_password: "{{ vault_stockmarket_db_root_password }}"
stockmarket_db_user_password: "{{ vault_stockmarket_db_password }}"
smtp_password: "{{ vault_smtp_password }}"
discord_webhook_url: "{{ vault_discord_webhook }}"
```

### 7.2 Environment File (.env)

```bash
# Generated from vault, never committed to git
DB_HOST=mariadb
DB_PORT=3306
DB_NAME=ksfraser_stock_market
DB_USER=ksfraser_stockmarket
DB_PASSWORD=<from_vault>
SMTP_HOST=localhost
SMTP_FROM=alerts@ksfraser.ca
SMTP_PASSWORD=<from_vault>
```

---

## 8. Monitoring Integration

The 3 business-critical jobs (Daily Monitor 7:30 AM, Stop Loss 8:00 AM, Price Alert 9 AM-4 PM) remain unchanged per user constraint. Only non-critical monitoring jobs migrate to this system.

---

## 9. Deployment Steps

1. Create Ansible role structure
2. Create shared Python modules
3. Refactor monitoring scripts
4. Initialize Vault secrets
5. Deploy to test environment
6. Run UAT tests
7. Deploy to production
8. Migrate non-critical cron jobs
9. Verify and decommission old Hermes jobs
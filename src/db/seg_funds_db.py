#!/usr/bin/env python3
"""
Segregated Fund Database Schema and Scraper System

DB: SQLite at ~/.hermes/cache/seg_funds.db

Tables:
- carriers: Insurance companies offering seg funds
- fund_families: Fund family/brand (e.g., "Manulife GIF Select")
- funds: Individual fund records (one per unique fund, regardless of series)
- fund_series: Series/load variants of each fund (FE, NLCB2, LL, BE, etc.)
- performance: Monthly/quarterly performance snapshots
- fund_codes: Cross-reference table for carrier-specific fund codes
- scrape_log: Track when each carrier was last scraped
"""

import os
import json
from datetime import datetime

from .connection import DataSource

DB_PATH = os.path.expanduser('~/.hermes/cache/seg_funds.db')

SCHEMA = """
-- Insurance carriers
CREATE TABLE IF NOT EXISTS carriers (
    carrier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    short_name TEXT NOT NULL,
    website TEXT,
    scrape_url TEXT,
    scrape_method TEXT DEFAULT 'browser',  -- browser, api, csv, pdf
    is_active INTEGER DEFAULT 1,
    last_scraped TEXT,
    scrape_status TEXT DEFAULT 'pending',
    notes TEXT
);

-- Fund families / product lines
CREATE TABLE IF NOT EXISTS fund_families (
    family_id INTEGER PRIMARY KEY AUTOINCREMENT,
    carrier_id INTEGER NOT NULL REFERENCES carriers(carrier_id),
    name TEXT NOT NULL,
    description TEXT,
    guarantee_type TEXT,  -- '75/75', '75/100', '100/100'
    UNIQUE(carrier_id, name)
);

-- Core fund table (one record per unique fund)
CREATE TABLE IF NOT EXISTS funds (
    fund_id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER REFERENCES fund_families(family_id),
    carrier_id INTEGER NOT NULL REFERENCES carriers(carrier_id),
    fund_name TEXT NOT NULL,
    fund_name_clean TEXT,  -- Normalized name for matching
    category TEXT,         -- 'Equity', 'Balanced', 'Fixed Income', 'Money Market', etc.
    risk_rating TEXT,      -- 'Low', 'Low-Medium', 'Medium', 'Medium-High', 'High'
    inception_date TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(carrier_id, fund_name)
);

-- Series/load variants (each fund can have multiple series)
CREATE TABLE IF NOT EXISTS fund_series (
    series_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL REFERENCES funds(fund_id),
    series_code TEXT NOT NULL,     -- 'FE', 'NLCB2', 'LL', 'BE', 'F', 'PSF', etc.
    series_name TEXT,              -- 'Front-End', 'No-Load CB2', 'Low-Load', etc.
    load_type TEXT,                -- 'front-end', 'no-load', 'low-load', 'back-end', 'f-class'
    mer REAL,                      -- Management Expense Ratio (%)
    msf REAL,                      -- Management Services Fee (%)
    guarantee_pct INTEGER,         -- Guarantee percentage (75 or 100)
    fund_status TEXT,              -- 'Open', 'Closed', 'Capped', 'Suspended'
    price REAL,                    -- Current NAV price
    price_date TEXT,
    price_change_1d REAL,
    price_change_1d_pct REAL,
    return_1m REAL,
    return_3m REAL,
    return_6m REAL,
    return_1y REAL,
    return_3y REAL,
    return_5y REAL,
    return_10y REAL,
    return_incept REAL,
    ytd_return REAL,
    yr_2025 REAL,
    yr_2024 REAL,
    yr_2023 REAL,
    yr_2022 REAL,
    yr_2021 REAL,
    yr_2020 REAL,
    yr_2019 REAL,
    as_at_date TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(fund_id, series_code)
);

-- Fund code cross-reference (carrier-specific codes)
CREATE TABLE IF NOT EXISTS fund_codes (
    code_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL REFERENCES funds(fund_id),
    carrier_id INTEGER NOT NULL REFERENCES carriers(carrier_id),
    code_type TEXT NOT NULL,       -- 'fund_code', 'cusip', 'isin', 'ticker'
    code_value TEXT NOT NULL,
    series_code TEXT,
    UNIQUE(carrier_id, code_type, code_value, series_code)
);

-- Performance history (monthly snapshots for trend tracking)
CREATE TABLE IF NOT EXISTS performance_history (
    perf_id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL REFERENCES fund_series(series_id),
    snapshot_date TEXT NOT NULL,
    price REAL,
    return_mtd REAL,
    return_1m REAL,
    return_3m REAL,
    return_6m REAL,
    return_1y REAL,
    return_3y REAL,
    return_5y REAL,
    return_10y REAL,
    return_incept REAL,
    ytd_return REAL,
    UNIQUE(series_id, snapshot_date)
);

-- Scrape log
CREATE TABLE IF NOT EXISTS scrape_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    carrier_id INTEGER NOT NULL REFERENCES carriers(carrier_id),
    scrape_time TEXT DEFAULT (datetime('now')),
    status TEXT,                   -- 'success', 'partial', 'failed'
    funds_found INTEGER DEFAULT 0,
    funds_new INTEGER DEFAULT 0,
    funds_updated INTEGER DEFAULT 0,
    errors TEXT,
    duration_seconds REAL
);

-- Screening presets
CREATE TABLE IF NOT EXISTS screening_presets (
    preset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    filters TEXT,                  -- JSON: {"min_return_1y": 5, "max_mer": 2.5, ...}
    sort_by TEXT DEFAULT 'return_1y',
    sort_order TEXT DEFAULT 'DESC',
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_funds_carrier ON funds(carrier_id);
CREATE INDEX IF NOT EXISTS idx_funds_category ON funds(category);
CREATE INDEX IF NOT EXISTS idx_funds_name ON funds(fund_name_clean);
CREATE INDEX IF NOT EXISTS idx_series_fund ON fund_series(fund_id);
CREATE INDEX IF NOT EXISTS idx_series_mer ON fund_series(mer);
CREATE INDEX IF NOT EXISTS idx_series_return_1y ON fund_series(return_1y);
CREATE INDEX IF NOT EXISTS idx_series_return_3y ON fund_series(return_3y);
CREATE INDEX IF NOT EXISTS idx_series_return_5y ON fund_series(return_5y);
CREATE INDEX IF NOT EXISTS idx_perf_series_date ON performance_history(series_id, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_codes_value ON fund_codes(code_value);
"""

CARRIERS = [
    ('Manulife', 'MFC', 'https://www.manulife.ca', 'https://funds.manulife.ca/en-US/profiles/', 'browser'),
    ('RBC Insurance', 'RBC', 'https://www.rbcroyalbank.com', None, 'csv'),
    ('BMO Insurance', 'BMO', 'https://www.bmo.com', 'https://www.bmofundcodes.com/gam/ca/advisor/products/fundslookup_english.html', 'browser'),
    ('Canada Life', 'CL', 'https://www.canadalife.com', 'https://canadalifemutualfunds.fundata.com/Default.aspx', 'browser'),
    ('iA Financial', 'IA', 'https://www.ia.ca', 'https://ia.ca/funds-performance', 'browser'),
    ('SSQ Insurance', 'SSQ', 'https://www.beneva.ca', 'https://www.beneva.ca/en/savings-investments/segregated-funds', 'browser'),
    ('Empire Life', 'EL', 'https://www.empire.ca', 'https://funds.empire.ca/seg-funds/en-US/SG01-a', 'browser'),
    ('Humania', 'HUM', 'https://www.humania.ca', None, 'login_required'),
    ('ivari', 'IVI', 'https://www.ivari.ca', 'https://rates.ivari.ca/EN/rates/default.asp?Lang=EN&ShowList=IP', 'browser'),
    ('Equitable Life', 'EQL', 'https://www.equitable.ca', 'https://www.equitable.ca/segregated-funds', 'browser'),
    ('Forresters', 'FOR', 'https://www.forresters.com', 'https://funds.cifinancial.com/en/funds/segregated/', 'browser'),
    ('VMO', 'VMO', 'https://www.vmo.ca', None, 'login_required'),
]


def get_db():
    """Get database connection, creating tables if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = DataSource.sqlite_connection(DB_PATH)
    return conn


def init_db():
    """Initialize the database schema and seed carriers."""
    conn = get_db()
    conn.executescript(SCHEMA)
    
    # Seed carriers
    for name, short, website, scrape_url, method in CARRIERS:
        conn.execute("""
            INSERT OR IGNORE INTO carriers (name, short_name, website, scrape_url, scrape_method)
            VALUES (?, ?, ?, ?, ?)
        """, (name, short, website, scrape_url, method))
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def get_carrier_id(conn, short_name):
    """Get carrier ID by short name."""
    row = conn.execute("SELECT carrier_id FROM carriers WHERE short_name = ?", (short_name,)).fetchone()
    return row['carrier_id'] if row else None


def upsert_fund(conn, carrier_id, fund_name, category=None, risk_rating=None, inception_date=None):
    """Insert or update a fund record."""
    # Clean name for matching
    clean_name = fund_name.strip()
    clean_name = ' '.join(clean_name.split())  # normalize whitespace
    
    existing = conn.execute(
        "SELECT fund_id FROM funds WHERE carrier_id = ? AND fund_name = ?",
        (carrier_id, fund_name)
    ).fetchone()
    
    if existing:
        conn.execute("""
            UPDATE funds SET
                category = COALESCE(?, category),
                risk_rating = COALESCE(?, risk_rating),
                inception_date = COALESCE(?, inception_date),
                updated_at = datetime('now')
            WHERE fund_id = ?
        """, (category, risk_rating, inception_date, existing['fund_id']))
        return existing['fund_id']
    else:
        cur = conn.execute("""
            INSERT INTO funds (carrier_id, fund_name, fund_name_clean, category, risk_rating, inception_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (carrier_id, fund_name, clean_name, category, risk_rating, inception_date))
        return cur.lastrowid


def upsert_series(conn, fund_id, series_code, **kwargs):
    """Insert or update a fund series record."""
    existing = conn.execute(
        "SELECT series_id FROM fund_series WHERE fund_id = ? AND series_code = ?",
        (fund_id, series_code)
    ).fetchone()
    
    fields = [
        'series_name', 'load_type', 'mer', 'msf', 'guarantee_pct', 'fund_status',
        'price', 'price_date', 'price_change_1d', 'price_change_1d_pct',
        'return_1m', 'return_3m', 'return_6m', 'return_1y', 'return_3y',
        'return_5y', 'return_10y', 'return_incept', 'ytd_return',
        'yr_2025', 'yr_2024', 'yr_2023', 'yr_2022', 'yr_2021', 'yr_2020', 'yr_2019',
        'as_at_date'
    ]
    
    if existing:
        set_clauses = ", ".join([f"{f} = COALESCE(?, {f})" for f in fields])
        set_clauses += ", updated_at = datetime('now')"
        values = [kwargs.get(f) for f in fields] + [existing['series_id']]
        conn.execute(f"UPDATE fund_series SET {set_clauses} WHERE series_id = ?", values)
        return existing['series_id']
    else:
        cols = ", ".join(fields)
        placeholders = ", ".join(["?" for _ in fields])
        values = [kwargs.get(f) for f in fields]
        cur = conn.execute(
            f"INSERT INTO fund_series (fund_id, series_code, {cols}) VALUES (?, ?, {placeholders})",
            [fund_id, series_code] + values
        )
        return cur.lastrowid


def log_scrape(conn, carrier_id, status, funds_found=0, funds_new=0, funds_updated=0, errors=None, duration=None):
    """Log a scrape run."""
    conn.execute("""
        INSERT INTO scrape_log (carrier_id, status, funds_found, funds_new, funds_updated, errors, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (carrier_id, status, funds_found, funds_new, funds_updated, errors, duration))
    conn.execute("""
        UPDATE carriers SET last_scraped = datetime('now'), scrape_status = ? WHERE carrier_id = ?
    """, (status, carrier_id))


if __name__ == '__main__':
    init_db()
    print("Seg Fund database initialized successfully.")

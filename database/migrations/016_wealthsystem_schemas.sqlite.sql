-- Migration 016: SQLite version of WealthSystem-aligned schemas
-- Safe to re-run

CREATE TABLE IF NOT EXISTS stock_fundamentals (
    symbol TEXT PRIMARY KEY,
    company_name TEXT,
    sector TEXT,
    industry TEXT,
    market_cap_bigint INTEGER,
    enterprise_value INTEGER,
    pe_ratio REAL,
    peg_ratio REAL,
    price_to_book REAL,
    price_to_sales REAL,
    debt_to_equity REAL,
    return_on_equity REAL,
    return_on_assets REAL,
    profit_margin REAL,
    operating_margin REAL,
    gross_margin REAL,
    dividend_yield REAL,
    payout_ratio REAL,
    beta REAL,
    revenue_growth REAL,
    earnings_growth REAL,
    current_ratio REAL,
    quick_ratio REAL,
    cash_per_share REAL,
    book_value_per_share REAL,
    analyst_rating TEXT,
    target_price REAL,
    last_updated TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evalbusiness (
    idevalbusiness INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    lasteval TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evalfinancial (
    idevalfinancial INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    lasteval TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evalmanagement (
    idevalmanagement INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    lasteval TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evalmarket (
    idevalmarket INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    lasteval TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evalsummary (
    symbol TEXT PRIMARY KEY,
    totalscore INTEGER NOT NULL DEFAULT -1,
    reviseddate TEXT DEFAULT (datetime('now')),
    marginsafety REAL NOT NULL DEFAULT -999999,
    ratioscore INTEGER DEFAULT 0,
    iplacecalcscore INTEGER DEFAULT 0,
    managementscore INTEGER NOT NULL DEFAULT -1,
    financialscore INTEGER NOT NULL DEFAULT -1,
    businessscore INTEGER NOT NULL DEFAULT -1,
    reviseduser TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS iplace_calc (
    idiplacecalc INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    composite_score INTEGER NOT NULL DEFAULT 0,
    recommendation TEXT,
    criteria_json TEXT,
    date_calculated TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS llm_analysis (
    idllmanalysis INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    analysis_date TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    management_openness INTEGER,
    candor_score INTEGER,
    moat_durability INTEGER,
    risk_factors TEXT,
    opportunities TEXT,
    summary TEXT,
    raw_response TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(symbol, analysis_date, provider)
);

CREATE TABLE IF NOT EXISTS stock_technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    sma_20 REAL,
    sma_50 REAL,
    sma_200 REAL,
    ema_12 REAL,
    ema_26 REAL,
    macd REAL,
    macd_signal REAL,
    macd_histogram REAL,
    rsi_14 REAL,
    bollinger_upper REAL,
    bollinger_middle REAL,
    bollinger_lower REAL,
    stochastic_k REAL,
    stochastic_d REAL,
    williams_r REAL,
    atr REAL,
    obv INTEGER,
    vwap REAL,
    golden_cross INTEGER DEFAULT 0,
    death_cross INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(symbol, date)
);

CREATE TABLE IF NOT EXISTS motleyfool (
    idmotleyfool INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    simplebusiness INTEGER DEFAULT 0,
    reasonablevaluation INTEGER DEFAULT 0,
    corefocus INTEGER DEFAULT 0,
    doubledigitsales INTEGER DEFAULT 0,
    risingcashflow INTEGER DEFAULT 0,
    risingbookvalue INTEGER DEFAULT 0,
    improvingmargins INTEGER DEFAULT 0,
    risingroe INTEGER DEFAULT 0,
    insiderownership INTEGER DEFAULT 0,
    regulardividend INTEGER DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    lastupdate TEXT DEFAULT (datetime('now')),
    UNIQUE(symbol)
);

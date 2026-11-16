#!/usr/bin/env python3
"""
Fund Screener Scoring Pipeline
================================
Computes the 4-formula scoring system for segregated funds:
  Formula 1: Effective LT Return (10yr with 5yr fallback)
  Formula 2: Weighted Composite Return (45/30/15/10)
  Formula 3: Risk-Adjusted Score (composite / std_dev)
  Formula 4: Hybrid Score (rank composite + rank std_dev)

Data source: MariaDB ksfraser_stock_market.fund_screener
"""

import os
import sys
import csv
import sqlalchemy
from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np
from urllib.parse import quote_plus

# Database connection
DB_HOST = os.environ.get('DB_HOST', 'ksfraser.ca')
DB_NAME = os.environ.get('DB_NAME', 'ksfraser_stock_market')
DB_USER = os.environ.get('DB_USER', 'ksfraser_stockmarket')
DB_PASS = os.environ.get('DB_PASS', 'Zaqwsx9sm1@')
DB_URL = f'mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASS)}@{DB_HOST}/{DB_NAME}'

def get_engine():
    """Create SQLAlchemy engine for MariaDB."""
    return create_engine(DB_URL)

def compute_scores(df):
    """
    Apply the 4-formula scoring system.
    
    Formula 1: Effective LT Return = 10yr with fallback to 5yr
    Formula 2: Weighted Composite = 45%*10yr + 30%*5yr + 15%*3yr + 10%*1yr
    Formula 3: Risk-Adjusted = composite / std_dev
    Formula 4: Hybrid = rank(composite) + rank(std_dev ascending)
    """
    # Reset index
    df = df.reset_index(drop=True)
    
    # Formula 1: Effective Long-Term Return
    df['eff_lt_return'] = df['return_10yr'].where(
        df['return_10yr'].notna(), 
        df['return_5yr']
    )
    
    # Formula 2: Weighted Composite Return
    df['composite_return'] = (
        0.45 * df['return_10yr'].fillna(df['return_5yr']) +
        0.30 * df['return_5yr'].fillna(0) +
        0.15 * df['return_3yr'].fillna(0) +
        0.10 * df['return_1yr'].fillna(0)
    )
    
    # Formula 3: Risk-Adjusted Score
    # Only compute where std_dev > 0
    df['risk_adjusted'] = np.where(
        df['std_dev'] > 0,
        df['composite_return'] / df['std_dev'],
        np.nan
    )
    
    # Formula 4: Hybrid Score
    # Need rank within all funds
    # Composite rank: higher is better (descending)
    # Std rank: lower is better (ascending)
    composite_rank = df['composite_return'].rank(ascending=False, method='average')
    std_rank = df['std_dev'].rank(ascending=True, method='average')
    df['hybrid_score'] = composite_rank + std_rank
    
    return df

def rank_funds(df):
    """Rank funds by composite_return (primary), risk_adjusted (secondary)."""
    df = df.copy()
    
    # Primary ranking: composite_return (higher better)
    # Secondary: risk_adjusted (higher better)
    df['rank_composite'] = df['composite_return'].rank(ascending=False, method='min')
    df['rank_risk_adj'] = df['risk_adjusted'].rank(ascending=False, method='min')
    
    # Composite score for ranking
    df['rank_total'] = df['rank_composite'] + df['rank_risk_adj']
    
    # Sort by composite_return, then composite_return (exact tiebreak)
    df = df.sort_values(['composite_return', 'composite_return'], 
                        ascending=[False, False]).reset_index(drop=True)
    
    # Assign final rank
    df['final_rank'] = range(1, len(df) + 1)
    
    return df

def filter_active_funds(df, min_10yr=None, min_5yr=None, min_composite=None):
    """Filter funds by minimum criteria."""
    df = df.copy()
    
    if min_10yr:
        df = df[df['return_10yr'] >= min_10yr]
    if min_5yr:
        df = df[df['return_5yr'] >= min_5yr]
    if min_composite:
        df = df[df['composite_return'] >= min_composite]
    
    return df

def print_summary(df, top_n=20):
    """Print summary of ranking."""
    print("=" * 80)
    print("FUND SCREENER - RANKED OUTPUT")
    print("=" * 80)
    print(f"\nTotal funds in database: {len(df)}")
    print(f"Funds with composite score: {df['composite_return'].notna().sum()}")
    print(f"Funds with std_dev: {df['std_dev'].notna().sum()}")
    print(f"Funds with risk_adjusted: {df['risk_adjusted'].notna().sum()}")
    
    print(f"\n{'Rank':<6} {'Carrier':<12} {'Fund Name':<55} {'10Y':>8} {'5Y':>8} {'3Y':>8} {'1Y':>8} {'StdDev':>8} {'Composite':>10} {'RiskAdj':>8}")
    print("-" * 150)
    
    top = df.nlargest(top_n, 'composite_return')
    for _, row in top.iterrows():
        rv10 = row['return_10yr']
        rv5 = row['return_5yr']
        rv3 = row['return_3yr']
        rv1 = row['return_1yr']
        sd = row['std_dev']
        cr = row['composite_return']
        ra = row['risk_adjusted']
        
        s10 = f"{rv10:.1f}" if pd.notna(rv10) else "N/A"
        s5 = f"{rv5:.1f}" if pd.notna(rv5) else "N/A"
        s3 = f"{rv3:.1f}" if pd.notna(rv3) else "N/A"
        s1 = f"{rv1:.1f}" if pd.notna(rv1) else "N/A"
        ss = f"{sd:.2f}" if pd.notna(sd) else "N/A"
        sc = f"{cr:.2f}" if pd.notna(cr) else "N/A"
        sa = f"{ra:.2f}" if pd.notna(ra) else "N/A"
        
        print(f"{row['final_rank']:<6} {str(row['carrier'])[:12]:<12} {str(row['fund_name'])[:55]:<55}")
        print(f"       10Y={s10:>8} 5Y={s5:>8} 3Y={s3:>8} 1Y={s1:>8} StdDev={ss:>8} Composite={sc:>10} RiskAdj={sa:>8}")
    
    # Top 5 by composite
    print("\n" + "=" * 80)
    print("TOP 5 FUNDS BY COMPOSITE RETURN")
    print("=" * 80)
    top5 = df.nlargest(5, 'composite_return')
    for _, row in top5.iterrows():
        print(f"  #{row['final_rank']}: {row['fund_name'][:55]} "
              f"(Carrier: {row['carrier']}, Composite: {row['composite_return']:.2f}%)")
    
    # Top 5 by risk-adjusted (if available)
    print("\n" + "=" * 80)
    print("TOP 5 FUNDS BY RISK-ADJUSTED SCORE")
    print("=" * 80)
    top_ra = df[df['risk_adjusted'].notna()].nlargest(5, 'risk_adjusted')
    for _, row in top_ra.iterrows():
        print(f"  #{row['final_rank']}: {row['fund_name'][:55]} "
              f"(Carrier: {row['carrier']}, RiskAdj: {row['risk_adjusted']:.2f})")
    
    return df

def save_rankings(df, output_path='fund_screener_ranked.csv'):
    """Save ranked funds to CSV."""
    df[['final_rank','carrier','fund_name','series','return_10yr','return_5yr',
        'return_3yr','return_1yr','std_dev','composite_return','risk_adjusted',
        'eff_lt_return']].to_csv(output_path, index=False)
    print(f"\nSaved ranked output to {output_path}")

def main():
    print("Connecting to MariaDB...")
    engine = get_engine()
    
    with engine.connect() as conn:
        # Query fund_screener view
        query = text("""
            SELECT 
                fund_code, fund_name, carrier, category, risk_rating, series,
                mer_pct, return_1yr, return_3yr, return_5yr, return_10yr,
                std_dev
            FROM fund_screener
        """)
        df = pd.read_sql(query, conn)
    
    print(f"Loaded {len(df)} funds from fund_screener view")
    
    # Compute scores
    print("\nComputing 4-formula scores...")
    df = compute_scores(df)
    
    # Rank
    df = rank_funds(df)
    
    # Filter out nulls (funds without any returns)
    df = df[df['composite_return'].notna()].reset_index(drop=True)
    
    # Convert risk_adjusted to numeric (handle None/strings from DB)
    df['risk_adjusted'] = pd.to_numeric(df['risk_adjusted'], errors='coerce')
    
    print(f"Funds with valid composite scores: {len(df)}")
    print(f"Funds with valid risk_adjusted: {df['risk_adjusted'].notna().sum()}")
    
    # Print summary
    print_summary(df, top_n=20)
    
    # Save to CSV
    save_rankings(df)
    
    # Also save risk-adjusted top 10
    df_ra = df[df['risk_adjusted'].notna()].nlargest(10, 'risk_adjusted')
    df_ra[['final_rank','carrier','fund_name','std_dev','composite_return','risk_adjusted']].to_csv(
        'fund_screener_top_risk_adjusted.csv', index=False)
    print("Saved top 10 by risk-adjusted to fund_screener_top_risk_adjusted.csv")
    
    return df

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Parameter Correlation & Redundancy Analysis (REQ-09)
===============================================
Computes correlation matrix from WeightOptimizer's signal_type_accuracy table.
Identifies high-correlation pairs (> |0.7|) — params that stand in for each other (redundant)
or strongly anti-correlated pairs (< -0.7) — contrarian signals.

Usage: python -m src.optimization.correlation_analysis
"""
import sqlite3, pandas as pd, numpy as np, sys, os
sys.path.insert(0, '.')

DB_PATH = 'analysis_results.db'


def compute_correlation(threshold=0.7):
    db = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT ticker, signal_type, win_rate FROM signal_type_accuracy", db)
    except Exception as e:
        print(f"Error reading signal_type_accuracy: {e}")
        return

    if df.empty:
        print("Data empty — no signal accuracy data available yet.")
        print("Run WeightOptimizer.optimize_all() first to populate signal_type_accuracy.")
        return

    pivot = df.pivot_table(index='ticker', columns='signal_type', values='win_rate')
    corr = pivot.corr()

    print("=== PARAMETER CORRELATION MATRIX ===")
    print(corr.round(3).to_string())

    pairs = []
    for i in corr.columns:
        for j in corr.columns:
            if i < j:
                val = corr.loc[i, j]
                if abs(val) > threshold:
                    pairs.append((i, j, val))

    print(f"\n=== HIGH CORRELATION PAIRS (|r| > {threshold}) ===")
    if pairs:
        for a, b, v in sorted(pairs, key=lambda x: -abs(x[2])):
            status = "REDUNDANT (stand in for each other)" if v > 0 else "CONTRARIAN (opposite signals)"
            print(f"  {a:15s} vs {b:15s}: r = {v:+.3f}  — {status}")
    else:
        print("No pairs with |correlation| > threshold.")
        print("Note: With sufficient data, high-correlation pairs indicate redundant signals (e.g., MA_ALIGN vs SMA200).")

    # Also show descriptive stats per ticker (for reference)
    print(f"\n=== DESCRIPTIVE STATS (per ticker) ===")
    for ticker, group in df.groupby('ticker'):
        avg_wr = group['win_rate'].mean()
        best_sig = group.loc[group['win_rate'].idxmax(), 'signal_type'] if not group.empty else 'N/A'
        print(f"  {ticker:6s}: avg win_rate={avg_wr:.2%}, best signal={best_sig}")


if __name__ == '__main__':
    compute_correlation(threshold=0.7)

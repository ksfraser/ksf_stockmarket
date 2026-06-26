#!/usr/bin/env python3
"""
Fix inactive symbols by:
1. Loading all known data-bearing symbols into memory
2. For each inactive symbol, generating cleaned candidates
3. If candidate has data in DB, update the record
4. For candidates without data, optionally try yfinance fetch
"""

import sys
sys.path.insert(0, 'python')

import mysql.connector
from config_loader import Config

def load_all_active_symbols(cnx):
    cursor = cnx.cursor()
    cursor.execute("SELECT DISTINCT symbol FROM stockprices")
    price_syms = {row[0] for row in cursor.fetchall()}
    
    cursor.execute("SELECT DISTINCT symbol FROM indicators_json")
    ind_syms = {row[0] for row in cursor.fetchall()}
    cursor.close()
    
    return price_syms | ind_syms

def generate_candidates(symbol):
    """Generate candidate clean symbols from a possibly malformed inactive symbol"""
    candidates = []
    original = symbol
    s = symbol
    
    # Remove common exchange prefixes
    prefixes = ['AMEX:', 'NYSE:', 'NASDAQ:', 'TSX:', 'TSXV:', 'NEO:', 'OTC:', 
                'LSE:', 'HKEX:', 'ASX:', 'CSE:', 'SSE:', 'SZSE:']
    for prefix in prefixes:
        if s.startswith(prefix):
            s = s[len(prefix):]
            candidates.append(s)
            break
    
    # If original has a US/OTC prefix AND ends with .TO, also try without .TO
    if original.startswith(('AMEX:', 'NYSE:', 'NASDAQ:', 'OTC:')) and s.endswith('.TO'):
        candidates.append(s[:-3])
    
    # If original has NEO: prefix and no .TO, try adding .TO
    if original.startswith('NEO:') and not s.endswith('.TO'):
        candidates.append(s + '.TO')
    
    # If original has TSX: prefix, try without it
    if original.startswith('TSX:'):
        candidates.append(s)
    
    # For OTC symbols, also try with base symbol (no .TO)
    if original.startswith('OTC:') and s.endswith('.TO'):
        candidates.append(s[:-3])
        # And try with -F suffix (common for OTC foreign stocks)
        candidates.append(s[:-3] + '-F')
    
    # Remove duplicate suffixes
    if s.endswith('.HK.HK'):
        candidates.append(s[:-3])
    
    # Remove duplicate suffix like .TO.TO (rare)
    if s.count('.TO') > 1:
        candidates.append(s.replace('.TO.TO', '.TO'))
    
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen and c != original:
            seen.add(c)
            unique.append(c)
    
    return unique

def main():
    config = Config('config.yaml')
    cnx = mysql.connector.connect(
        host=config.data.db_host,
        database=config.data.db_name,
        user=config.data.db_user,
        password=config.db_password
    )
    
    active_syms = load_all_active_symbols(cnx)
    print(f"Symbols with data: {len(active_syms)}")
    
    cursor = cnx.cursor()
    cursor.execute("""
        SELECT symbol, exchange, name, deactivated_reason
        FROM symbol_master
        WHERE is_active = 0
        ORDER BY symbol
    """)
    inactive = cursor.fetchall()
    
    print(f"Total inactive: {len(inactive)}")
    
    fixed = 0
    skipped = 0
    no_candidate = 0
    errors = []
    already_active = 0
    
    for i, row in enumerate(inactive):
        symbol = row[0]
        exchange = row[1]
        reason = row[3]
        
        if i % 100 == 0 and i > 0:
            print(f"  Processed {i}/{len(inactive)}...")
        
        if reason is not None and 'duplicate format' in str(reason):
            skipped += 1
            continue
        
        # Check if current symbol has data
        if symbol in active_syms:
            cursor.execute("""
                UPDATE symbol_master
                SET is_active = 1,
                    deactivated_at = NULL,
                    deactivated_reason = NULL,
                    exchange = COALESCE(exchange, 'UNKNOWN')
                WHERE symbol = %s
            """, [symbol])
            fixed += 1
            continue
        
        candidates = generate_candidates(symbol)
        
        found = None
        for candidate in candidates:
            if candidate in active_syms:
                found = candidate
                break
        
        if found:
            print(f"  FIX: {symbol} -> {found}")
            
            cursor.execute(
                "SELECT symbol FROM symbol_master WHERE symbol = %s AND is_active = 1",
                [found]
            )
            existing = cursor.fetchone()
            
            if existing:
                print(f"    -> {found} already active, marking {symbol} as duplicate")
                cursor.execute("""
                    UPDATE symbol_master
                    SET exchange = NULL,
                        name = CONCAT(IFNULL(name,''), ' [DUPLICATE of ', %s, ']'),
                        deactivated_reason = %s,
                        deactivated_at = NOW()
                    WHERE symbol = %s
                """, [found, f'duplicate - superseded by {found}', symbol])
                already_active += 1
            else:
                cursor.execute("""
                    UPDATE symbol_master
                    SET symbol = %s,
                        exchange = COALESCE(exchange, 'UNKNOWN'),
                        is_active = 1,
                        deactivated_at = NULL,
                        deactivated_reason = NULL
                    WHERE symbol = %s
                """, [found, symbol])
            fixed += 1
        else:
            no_candidate += 1
    
    cnx.commit()
    cursor.close()
    cnx.close()
    
    print(f"\n=== Summary ===")
    print(f"Total inactive: {len(inactive)}")
    print(f"Fixed/reactivated: {fixed}")
    print(f"  (corrected mapping): {fixed - already_active}")
    print(f"  (already active duplicates): {already_active}")
    print(f"Skipped (duplicate entries): {skipped}")
    print(f"No candidate found: {no_candidate}")
    print(f"Errors: {len(errors)}")

if __name__ == '__main__':
    main()

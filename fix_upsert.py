#!/usr/bin/env python3
"""Fix the upsert in migrate_indicators_json_to_columnar.py — correct parameter ordering."""
from pathlib import Path
p = Path('/home/ksf_stockmarket/ksf_stockmarket/migrate_indicators_json_to_columnar.py')
src = p.read_text()

old_block = """    # 5. Build upsert
    dto_dict = dto.to_dict()
    fields_to_write = sorted(dto_dict.keys())
    fields_in_db = [f for f in fields_to_write if f in existing_cols]

    if not fields_in_db:
        print(f"  [WARN] No DTO fields match existing columns (all {len(fields_to_write)} are missing?)")
        # If all fields are missing, we just added them — re-read
        upsert_sql = (
            f"INSERT INTO indicators (symbol, price_date, {', '.join(f'`{c}`' for c in fields_in_db)}) "
            f"VALUES (%s, %s, {', '.join(['%s'] * len(fields_in_db))}) "
            f"ON DUPLICATE KEY UPDATE {', '.join(f'`{f}` = VALUES(`{f}`)' for f in fields_in_db)}"
        )
        # parameter order MUST match: symbol, price_date, then field values
        values = [jsymbol, jdate] + [field_to_db_value(dto_dict[f]) for f in fields_in_db]

    if not fields_in_db:
        print(f"  [SKIP] No columns to write for this row")
        return {'skipped': 1, 'migrated': 0, 'errors': 1}

    print(f"\\n  --- Upserting {len(fields_in_db)} fields ---")
    for f in fields_in_db:
        print(f"    {f} = {dto_dict[f]!r} -> {field_to_db_value(dto_dict[f])!r}")

    if not dry_run:
        upsert_sql = (
            f"INSERT INTO indicators (symbol, price_date, {', '.join(f'`{f}`' for f in fields_in_db)}) "
            f"VALUES (%s, %s, {', '.join(['%s'] * len(fields_in_db))}) "
            f"ON DUPLICATE KEY UPDATE {', '.join(f'`{f}` = VALUES(`{f}`)' for f in fields_in_db)}"
        )
        try:
            cur.execute(upsert_sql, values)
            print(f"  -> Upserted (rows affected: {cur.rowcount})")
        except Exception as e:
            print(f"  [ERROR] Upsert failed: {e}")
            return {'skipped': 0, 'migrated': 0, 'errors': 1}
"""

new_block = """    # 5. Build upsert — parameter order: symbol, price_date, then field values
    dto_dict = dto.to_dict()
    fields_to_write = sorted(dto_dict.keys())
    fields_in_db = [f for f in fields_to_write if f in existing_cols]

    if not fields_in_db:
        print(f"  [SKIP] No DTO fields match existing columns (all {len(fields_to_write)} are missing?)")
        return {'skipped': 1, 'migrated': 0, 'errors': 1}

    print(f"\\n  --- Upserting {len(fields_in_db)} fields ---")
    for f in fields_in_db:
        print(f"    {f} = {dto_dict[f]!r} -> {field_to_db_value(dto_dict[f])!r}")

    if not dry_run:
        upsert_sql = (
            f"INSERT INTO indicators (symbol, price_date, {', '.join(f'`{f}`' for f in fields_in_db)}) "
            f"VALUES (%s, %s, {', '.join(['%s'] * len(fields_in_db))}) "
            f"ON DUPLICATE KEY UPDATE {', '.join(f'`{f}` = VALUES(`{f}`)' for f in fields_in_db)}"
        )
        values = [jsymbol, jdate] + [field_to_db_value(dto_dict[f]) for f in fields_in_db]
        try:
            cur.execute(upsert_sql, values)
            print(f"  -> Upserted (rows affected: {cur.rowcount})")
        except Exception as e:
            print(f"  [ERROR] Upsert failed: {e}")
            conn.rollback()
            return {'skipped': 0, 'migrated': 0, 'errors': 1}
"""

assert old_block in src, f"Old block NOT found (checking exact match)"
src = src.replace(old_block, new_block, 1)
p.write_text(src)
print("Fixed upsert parameter ordering")

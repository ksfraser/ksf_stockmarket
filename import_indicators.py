#!/usr/bin/env python3
"""
Import SQLite ta_indicators into MariaDB indicators table.
"""
from __future__ import annotations
import argparse
import logging
import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pymysql
import pymysql.cursors


logger = logging.getLogger(__name__)


def _config_loader():
    for mod_name in ('python.config_loader', 'config_loader'):
        try:
            module = __import__(mod_name, fromlist=['Config'])
            return module.Config
        except ModuleNotFoundError:
            continue
    raise ModuleNotFoundError('config_loader module not found')


def _find_config() -> str:
    candidates = [
        Path(__file__).resolve().parent / '..' / 'config.yaml',
        Path(__file__).resolve().parent / '..' / '..' / 'config.yaml',
        os.environ.get('KFSF_CONFIG', ''),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    return os.environ.get('KFSF_CONFIG', '')


def _db_cfg():
    cfg_cls = _config_loader()
    cfg_path = _find_config()
    cfg = cfg_cls(cfg_path)
    data_cfg = cfg.data if hasattr(cfg, 'data') and cfg.data else {}
    secrets = getattr(cfg, 'secrets', {}) or {}
    merged = {**data_cfg, **secrets}
    password = (
        merged.get('db_password')
        or merged.get('db_pass')
        or os.environ.get('DB_PASSWORD')
        or os.environ.get('MYSQL_PASSWORD')
        or os.environ.get('DB_PASS', '')
    )
    host = merged.get('db_host') or os.environ.get('DB_HOST', 'ksfraser.ca')
    port = int(merged.get('db_port') or os.environ.get('DB_PORT', '3306'))
    username = merged.get('db_user') or os.environ.get('DB_USER', 'ksfraser_stockmarket')
    database = merged.get('db_name') or os.environ.get('DB_NAME', 'ksfraser_stock_market')
    return {
        'host': host,
        'port': port,
        'user': username,
        'password': password,
        'database': database,
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False,
    }


def _open_sqlite() -> sqlite3.Connection:
    sqlite_path = '/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db'
    if not Path(sqlite_path).exists():
        raise FileNotFoundError(f'SQLite file not found: {sqlite_path}')
    return sqlite3.connect(sqlite_path)


def _open_mariadb():
    cfg = _db_cfg()
    if not cfg['password']:
        raise RuntimeError(
            'MariaDB password is not set. Provide db_password in config.yaml/vault or DB_PASSWORD/DB_PASS in env.'
        )
    return pymysql.connect(**cfg)


def _norm(name: str) -> str:
    normalized = name.lower()
    normalized = normalized.replace('bbands_', 'bb_')
    normalized = normalized.replace('_1d5', '_1_5').replace('_2d0', '_2_0').replace('_2d5', '_2_5')
    return normalized


def _build_column_mapping(sqlite_cursor: pymysql.cursors.Cursor, mariadb_cursor: pymysql.cursors.Cursor):
    sqlite_cursor.execute('PRAGMA table_info(ta_indicators)')
    sqlite_cols: List[str] = [row[1] for row in sqlite_cursor.fetchall()]
    mariadb_cursor.execute('DESCRIBE indicators')
    mariadb_cols: List[str] = [row[0] for row in mariadb_cursor.fetchall()]
    normalized_map = {_norm(col): col for col in mariadb_cols}
    mapping = {sqlite_col: normalized_map[_norm(sqlite_col)] for sqlite_col in sqlite_cols if _norm(sqlite_col) in normalized_map}
    return sqlite_cols, mariadb_cols, mapping


def _execute_import(args: argparse.Namespace) -> int:
    sqlite_path = args.sqlite if args.sqlite else '/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db'
    if not Path(sqlite_path).exists():
        raise FileNotFoundError(f'SQLite file not found: {sqlite_path}')

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    mariadb_conn = _open_mariadb()
    mariadb_cursor = mariadb_conn.cursor()

    try:
        sqlite_cursor.execute('PRAGMA table_info(ta_indicators)')
        if not sqlite_cursor.fetchall():
            logger.info('SQLite ta_indicators is empty. Nothing to import.')
            return 0

        sqlite_cols, mariadb_cols, mapping = _build_column_mapping(sqlite_cursor, mariadb_cursor)
        if not mapping:
            logger.error('No overlapping columns between SQLite ta_indicators and MariaDB indicators.')
            return 2

        base_cols = ['symbol', 'price_date']
        data_sqlite_cols = [col for col in sqlite_cols if col not in base_cols and col in mapping]
        data_mariadb_cols = [mapping[col] for col in data_sqlite_cols]
        all_columns = base_cols + data_mariadb_cols
        column_ids = ', '.join(f'`{col}`' for col in all_columns)

        select_columns = ', '.join(f'"{col}"' for col in (base_cols + data_sqlite_cols))
        sqlite_cursor.execute(f'SELECT {select_columns} FROM ta_indicators')
        rows: List[Sequence[object]] = sqlite_cursor.fetchall()
        total_rows = len(rows)
        logger.info('Rows: %s, Columns: %s', f'{total_rows:,}', len(all_columns))

        insert_sql = f'INSERT IGNORE INTO indicators ({column_ids}) VALUES ({",".join(["%s"] * len(all_columns))})'

        inserted = 0
        errors = 0
        for idx, row in enumerate(rows, start=1):
            try:
                mariadb_cursor.execute(insert_sql, tuple(row))
                inserted += 1
            except Exception as exc:
                errors += 1
                if errors <= 3:
                    logger.error('ERR on row %s: %s', idx, exc)
            if inserted % 1000 == 0:
                mariadb_conn.commit()
                logger.info('  %s/%s (%s%%)', f'{inserted:,}', f'{total_rows:,}', f'{inserted / total_rows * 100:.0f}')

        mariadb_conn.commit()
        mariadb_cursor.execute('SET FOREIGN_KEY_CHECKS=1')
        mariadb_cursor.execute('SELECT COUNT(*) FROM indicators')
        count = mariadb_cursor.fetchone()[0]
        logger.info('Done! Total rows: %s, Inserted: %s, Errors: %s', f'{count:,}', f'{inserted:,}', f'{errors:,}')
        return 0
    finally:
        mariadb_cursor.close()
        mariadb_conn.close()
        sqlite_cursor.close()
        sqlite_conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Import SQLite ta_indicators into MariaDB indicators table.')
    parser.add_argument('--sqlite', default='/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db', help='Path to SQLite file')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    args = parse_args()
    return _execute_import(args)


if __name__ == '__main__':
    raise SystemExit(main())

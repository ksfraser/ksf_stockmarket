#!/usr/bin/env python3
"""
config_provider.py — Centralized MariaDB/database configuration provider.

Reads from config.yaml (data: section) + Ansible Vault (secrets:).
Falls back to environment variables only for overrides.
"""
from __future__ import annotations

import os
import yaml
import subprocess
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class _VaultConfigProvider:
    """Read database config from config.yaml and vault."""

    def __init__(self, config_path: str = 'config.yaml') -> None:
        self._config_path = config_path
        self._secrets: Dict[str, Any] = {}
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        path = self._resolve_path()
        if not path or not os.path.isfile(path):
            raise FileNotFoundError(f"config.yaml not found at {path}")

        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        self._data = raw.get('data', {}) or {}

        vault_cfg = raw.get('vault', {}) or {}
        vault_path = vault_cfg.get('vault_path', '')
        pw_file = vault_cfg.get('vault_password_file', '')

        if vault_path and pw_file:
            if not os.path.isabs(vault_path):
                vault_path = os.path.join(os.path.dirname(os.path.abspath(path)), vault_path)
            if not os.path.isabs(pw_file):
                pw_file = os.path.join(os.path.dirname(os.path.abspath(path)), pw_file)

            if os.path.isfile(vault_path):
                try:
                    result = subprocess.run(
                        ['ansible-vault', 'view', '--vault-password-file', pw_file, vault_path],
                        capture_output=True, text=True, check=True,
                    )
                    vault_data = yaml.safe_load(result.stdout) or {}
                    self._secrets = vault_data
                except Exception as e:
                    logger.warning("Failed to decrypt vault %s: %s", vault_path, e)

    def _resolve_path(self) -> str:
        candidates = [
            self._config_path,
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', self._config_path),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', self._config_path),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return os.path.abspath(c)
        return self._config_path

    def get_db_config(self) -> Dict[str, Any]:
        """Return a dict with db_host, db_name, db_user, db_password."""
        cfg = {
            'host': os.environ.get('DB_HOST') or self._data.get('db_host', 'ksfraser.ca'),
            'port': int(os.environ.get('DB_PORT', '3306')),
            'database': os.environ.get('DB_NAME') or self._data.get('db_name', 'ksfraser_stock_market'),
            'user': os.environ.get('DB_USER') or self._data.get('db_user', 'ksfraser_stockmarket'),
            'charset': os.environ.get('DB_CHARSET', 'utf8mb4'),
            'cursorclass': None,  # filled by caller
            'autocommit': True,
        }

        password = (
            self._secrets.get('db_password')
            or self._secrets.get('db_pass')
            or os.environ.get('DB_PASSWORD')
            or os.environ.get('DB_PASS', '')
        )
        cfg['password'] = password
        return cfg

    @property
    def secrets(self) -> Dict[str, Any]:
        return self._secrets

    @property
    def data(self) -> Dict[str, Any]:
        return self._data


# Module-level singleton
_provider: Optional[_VaultConfigProvider] = None


def get_provider() -> _VaultConfigProvider:
    global _provider
    if _provider is None:
        _provider = _VaultConfigProvider()
    return _provider


def get_db_config() -> Dict[str, Any]:
    return get_provider().get_db_config()


def get_password() -> str:
    return get_db_config().get('password', '')


def get_host() -> str:
    return get_db_config().get('host', 'ksfraser.ca')


def get_name() -> str:
    return get_db_config().get('database', 'ksfraser_stock_market')


def get_user() -> str:
    return get_db_config().get('user', 'ksfraser_stockmarket')


if __name__ == '__main__':
    import json
    p = get_provider()
    print(json.dumps({k: '***' if 'password' in k else v for k, v in p.get_db_config().items()}, indent=2))

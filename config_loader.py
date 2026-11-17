"""config_loader — load configuration for the ksf_stockmarket cron queue.

Reads config.yaml (data: section) plus the group_vars vault for secrets
(db_password). Exposes a ``Config`` object whose ``data`` and ``secrets``
attributes provide attribute-style access, matching the interface the
cron_queue.py ``_get_db_config`` expects.

Note: group_vars/vault.yml is plain YAML (not ansible-vault encrypted), so we
read it directly rather than going through ``ansible-vault``.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml


class _ConfigData:
    """Attribute-style view over a mapping. Nested dicts become nested objects."""

    def __init__(self, mapping):
        for key, value in mapping.items():
            if isinstance(value, dict):
                value = _ConfigData(value)
            setattr(self, key, value)


class Config:
    """Configuration object backed by config.yaml + vault secrets."""

    def __init__(self, config_path):
        self._config_path = Path(config_path).resolve()
        with self._config_path.open(encoding="utf-8") as fh:
            self._raw = yaml.safe_load(fh) or {}

        self._data = self._raw.get("data", {}) or {}
        # cron_queue.py defaults db_port to 3306 when it is absent.
        self._data.setdefault("db_port", 3306)

        self._secrets = self._load_secrets()

    def _load_secrets(self):
        vault = self._raw.get("vault", {}) or {}
        vault_path = vault.get("vault_path", "")
        if not vault_path:
            return {}
        candidate = Path(vault_path)
        if not candidate.is_absolute():
            candidate = self._config_path.parent / vault_path
        if not candidate.is_file():
            return {}
        with candidate.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    @property
    def data(self):
        return _ConfigData(self._data)

    @property
    def secrets(self):
        return self._secrets

    @property
    def db_password(self):
        return self._secrets.get("db_password") or os.environ.get("DB_PASS", "")


def get_config(config_path):
    return Config(config_path)

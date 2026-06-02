#!/usr/bin/env python3
"""
config_loader.py — Load and validate config.yaml with attribute-style access.
Supports Ansible Vault for secrets: set vault_path and vault_password_file
under the 'vault:' key in config.yaml. Decrypted values are available as
config.secrets (a plain dict), and automatically merged so config.data.password
works transparently.

Usage:
    from config_loader import Config
    config = Config('config.yaml')
    print(config.screener.min_price)
    pw = config.secrets.get('db_password')
"""
import yaml
import os
import sys
import subprocess
import tempfile


def _decrypt_vault(vault_path: str, password_file: str) -> dict:
    """Decrypt an Ansible Vault YAML file and return its contents as a dict."""
    result = subprocess.run(
        ['ansible-vault', 'view',
         '--vault-password-file', password_file,
         vault_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to decrypt vault {vault_path}: {result.stderr.strip()}"
        )
    data = yaml.safe_load(result.stdout)
    return data if isinstance(data, dict) else {}


class ConfigNode:
    """Attribute-style access to nested dict."""

    def __init__(self, data: dict):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigNode(value))
            elif isinstance(value, list):
                setattr(self, key, [ConfigNode(i) if isinstance(i, dict) else i for i in value])
            else:
                setattr(self, key, value)

    def __repr__(self):
        attrs = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        return f"ConfigNode({attrs})"

    def get(self, key, default=None):
        return getattr(self, key, default)

    def to_dict(self) -> dict:
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, ConfigNode):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [i.to_dict() if isinstance(i, ConfigNode) else i for i in value]
            else:
                result[key] = value
        return result


class Config:
    """Root config object."""

    def __init__(self, path: str = None):
        if path is None:
            # Try common locations
            for p in ['config.yaml', 'ksf_stockmarket/config.yaml',
                      os.path.join(os.path.dirname(__file__), '..', 'config.yaml')]:
                if os.path.exists(p):
                    path = p
                    break

        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"config.yaml not found. Tried: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        self._raw = data
        self._path = path

        # ── Decrypt vault if configured ──────────────────────────────────
        self.secrets: dict = {}
        vault_cfg = data.get('vault', {})
        if vault_cfg.get('vault_path'):
            vault_path = vault_cfg['vault_path']
            pw_file = vault_cfg.get('vault_password_file', '')
            # Resolve relative paths against config.yaml's directory
            if not os.path.isabs(vault_path):
                vault_path = os.path.join(os.path.dirname(os.path.abspath(path)), vault_path)
            if pw_file and not os.path.isabs(pw_file):
                pw_file = os.path.join(os.path.dirname(os.path.abspath(path)), pw_file)
            if os.path.exists(vault_path):
                self.secrets = _decrypt_vault(vault_path, pw_file) if pw_file else {}

        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigNode(value))
            elif isinstance(value, list):
                setattr(self, key, [ConfigNode(i) if isinstance(i, dict) else i for i in value])
            else:
                setattr(self, key, value)

        # Convenience: secrets accessible as config.db_password etc.
        for _skey, _sval in self.secrets.items():
            if not hasattr(self, _skey):
                setattr(self, _skey, _sval)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def to_dict(self):
        return self._raw

    @property
    def yaml_path(self):
        return self._path

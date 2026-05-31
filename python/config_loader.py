#!/usr/bin/env python3
"""
config_loader.py — Load and validate config.yaml with attribute-style access.

Usage:
    from config_loader import Config
    config = Config('config.yaml')
    print(config.screener.min_price)
    print(config.accounts.tfsa.initial_balance)
"""
import yaml
import os
import sys


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

        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigNode(value))
            elif isinstance(value, list):
                setattr(self, key, [ConfigNode(i) if isinstance(i, dict) else i for i in value])
            else:
                setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def to_dict(self):
        return self._raw

    @property
    def yaml_path(self):
        return self._path

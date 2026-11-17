"""Backward-compatibility shim.

``AlertDTO`` now lives in the canonical ``dto`` package (see ``dto/alert.py``).
Re-exported here so existing ``from db.alert_dto import AlertDTO`` imports keep
working during the layered-architecture migration.
"""
from dto.alert import AlertDTO

__all__ = ["AlertDTO"]

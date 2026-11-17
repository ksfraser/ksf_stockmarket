"""Backward-compatibility shim.

``StockPriceDTO`` / ``to_ohlcv_dataframe`` now live in the canonical ``dto``
package (see ``dto/price.py``). This module re-exports them so existing
``from db.stock_price_dto import ...`` imports keep working during the
layered-architecture migration.
"""
from dto.price import StockPriceDTO, to_ohlcv_dataframe

__all__ = ["StockPriceDTO", "to_ohlcv_dataframe"]

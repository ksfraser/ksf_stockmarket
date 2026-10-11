"""
investment-agent/src/db — data layer.

Public surface:
  - StockPriceDTO: canonical price bar
  - StockPriceRepository: read/write interface
  - SQLitePriceRepository: intraday / ephemeral cache
  - MariaDBStockPriceRepository: daily+ history
  - PriceFetcher: external source interface
  - YFinanceFetcher: yfinance daily OHLCV fetcher
  - get_repository: factory selecting backend by config/sqlite_mode
"""

from .stock_price_dto import StockPriceDTO
from .stock_price_repository import StockPriceRepository
from .sqlite_price_repository import SQLitePriceRepository
from .mariadb_price_repository import MariaDBStockPriceRepository
from .price_fetcher import PriceFetcher, YFinanceFetcher


def get_repository(sqlite_mode: bool = False, **mariadb_cfg):
    """Factory: return SQLite or MariaDB repository."""
    if sqlite_mode:
        from config.paths import ANALYTICS_DB
        return SQLitePriceRepository(db_path=str(ANALYTICS_DB))
    return MariaDBStockPriceRepository(**mariadb_cfg)

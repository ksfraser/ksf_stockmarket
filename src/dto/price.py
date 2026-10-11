"""Canonical price DTO and helpers."""

class StockPriceDTO:
    def __init__(self, symbol, price_date, open=None, high=None, low=None, close=None, volume=None):
        self.symbol = symbol
        self.price_date = price_date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

    def __repr__(self):
        return f"StockPriceDTO({self.symbol}, {self.price_date})"

def to_ohlcv_dataframe(dtos):
    """Convert list of StockPriceDTO to pandas DataFrame."""
    import pandas as pd
    data = []
    for dt in dtos:
        data.append({
            'symbol': dt.symbol,
            'price_date': dt.price_date,
            'open': dt.open,
            'high': dt.high,
            'low': dt.low,
            'close': dt.close,
            'volume': dt.volume,
        })
    return pd.DataFrame(data)

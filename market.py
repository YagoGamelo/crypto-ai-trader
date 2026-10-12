"""Public OHLCV market data; never places orders."""
import ccxt
import pandas as pd

def candles(symbol="BTC/USD", timeframe="1h", limit=720):
    exchange = ccxt.kraken({"enableRateLimit": True, "timeout": 20000})
    rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if len(rows) < 120:
        raise ValueError("Not enough market candles")
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    # Most recent candle may still be forming.
    return df.iloc[:-1].reset_index(drop=True)

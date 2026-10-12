"""Batch market screener: research signals only, no real orders."""
import pandas as pd
import numpy as np
import yfinance as yf
from catalog import WATCHLIST

def scan(limit=150):
    assets = WATCHLIST[:limit]
    symbols = [x["symbol"] for x in assets]
    frames = []
    # Batches limit the size of each request and allow partial failures.
    for start in range(0, len(symbols), 15):
        batch = symbols[start:start + 15]
        try:
            data = yf.download(batch, period="1y", interval="1d",
                               group_by="ticker", auto_adjust=True,
                               progress=False, threads=True, timeout=15)
        except Exception:
            continue
        for symbol in batch:
            try:
                d = data[symbol] if isinstance(data.columns, pd.MultiIndex) else data
                close = d["Close"].dropna()
                volume = d["Volume"].reindex(close.index).fillna(0)
                if len(close) < 100:
                    continue
                ma20 = close.rolling(20).mean().iloc[-1]
                ma50 = close.rolling(50).mean().iloc[-1]
                momentum = close.iloc[-1] / close.iloc[-21] - 1
                volatility = close.pct_change().tail(30).std()
                # Heuristic score only; NOT a calibrated win probability.
                bullish = close.iloc[-1] > ma20 > ma50 and momentum > 0
                bearish = close.iloc[-1] < ma20 < ma50 and momentum < 0
                signal = "COMPRAR (candidato)" if bullish else ("VENDER (se detido)" if bearish else "ESPERAR")
                frames.append({
                    "Ativo": symbol,
                    "Mercado": next(x["category"] for x in assets if x["symbol"] == symbol),
                    "Preço USD": round(float(close.iloc[-1]), 5),
                    "Momento 20d %": round(float(momentum * 100), 2),
                    "Volatilidade diária %": round(float(volatility * 100), 2),
                    "Sinal técnico": signal,
                    "Data última vela": str(close.index[-1].date()),
                })
            except Exception:
                continue
    return pd.DataFrame(frames)

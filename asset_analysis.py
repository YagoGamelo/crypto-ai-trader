"""Per-asset daily chart and experimental out-of-sample direction forecasts."""
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf
from research_v2 import research_direction

def history(symbol, period="2y"):
    raw = yf.download(symbol, period=period, interval="1d", auto_adjust=True,
                      progress=False, threads=False, timeout=20)
    if raw.empty:
        raise ValueError("Sem dados para este ativo")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.rename(columns=str.title)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if not all(k in raw for k in required):
        raise ValueError("Dados OHLCV incompletos")
    result=raw[required].dropna(subset=["Close"]).copy()
    # Never use today's partly formed daily candle in a forecast.
    today_utc=datetime.now(timezone.utc).date()
    result=result.loc[pd.DatetimeIndex(result.index).date < today_utc]
    if len(result)<300:
        raise ValueError("Histórico completo insuficiente")
    return result

def indicators(raw):
    x = raw.copy()
    x["Ret1"] = x.Close.pct_change()
    x["Ret5"] = x.Close.pct_change(5)
    x["Ret20"] = x.Close.pct_change(20)
    x["MA20"] = x.Close.rolling(20).mean()
    x["MA50"] = x.Close.rolling(50).mean()
    x["Vol20"] = x.Ret1.rolling(20).std()
    delta = x.Close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    x["RSI14"] = 100 - 100 / (1 + gains / losses.replace(0, np.nan))
    x["VolumeRatio"] = x.Volume / x.Volume.rolling(20).mean().replace(0, np.nan)
    return x

def forecast(raw, horizon):
    """Use exactly the same calibrated model as the global research table."""
    if horizon not in (1,5,20):
        raise ValueError("Horizonte inválido")
    result=research_direction(raw["Close"],horizon=horizon)
    if result is None:
        raise ValueError("Histórico insuficiente para treino, calibração e teste independentes")
    return {
        "p_up":result["up_pct"]/100,
        "p_down":result["down_pct"]/100,
        "horizon":horizon,
        "brier":result["brier"],
        "baseline":result["baseline_brier"],
        "accuracy":result["holdout_accuracy"],
        "samples":result["holdout_count"],
        "ece":result["ece"],
        "high_confidence_count":result["bullish_signals"],
        "approved_for_paper":result["approved_for_paper"],
        "better_than_baseline":result["better_than_baseline"],
        "last_date":str(pd.Timestamp(raw.index[-1]).date()),
    }

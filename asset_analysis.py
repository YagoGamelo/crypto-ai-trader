"""Per-asset daily chart and experimental out-of-sample direction forecasts."""
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

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
    return raw[required].dropna(subset=["Close"]).copy()

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

FEATURES = ["Ret1", "Ret5", "Ret20", "Vol20", "RSI14", "VolumeRatio", "DistMA20", "DistMA50"]

def forecast(raw, horizon):
    if horizon not in (1, 5, 20):
        raise ValueError("Horizonte inválido")
    x = indicators(raw)
    x["DistMA20"] = x.Close / x.MA20 - 1
    x["DistMA50"] = x.Close / x.MA50 - 1
    x["Forward"] = x.Close.shift(-horizon) / x.Close - 1
    labeled = x.iloc[:-horizon].dropna(subset=FEATURES + ["Forward"]).copy()
    if len(labeled) < 180:
        raise ValueError("Histórico insuficiente para validar este prazo")
    labeled["Up"] = (labeled.Forward > 0).astype(int)
    split = int(len(labeled) * 0.7)
    train = labeled.iloc[:split-horizon]
    test = labeled.iloc[split:]
    if train.Up.nunique() < 2 or test.Up.nunique() < 2:
        raise ValueError("Pouca diversidade nos resultados históricos")
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(train[FEATURES], train.Up)
    predicted = model.predict_proba(test[FEATURES])[:, 1]
    brier = float(brier_score_loss(test.Up, predicted))
    baseline = float(brier_score_loss(test.Up, np.full(len(test), train.Up.mean())))
    accuracy = float(((predicted >= 0.5) == test.Up.to_numpy()).mean())
    latest = x.iloc[[-1]][FEATURES]
    if latest.isna().any().any():
        raise ValueError("Indicadores recentes incompletos")
    # Refit using fully labeled history, leaving current unobserved horizon out.
    model.fit(labeled[FEATURES], labeled.Up)
    p_up = float(model.predict_proba(latest)[0, 1])
    return {
        "p_up": p_up, "p_down": 1-p_up, "horizon": horizon,
        "brier": brier, "baseline": baseline, "accuracy": accuracy,
        "samples": len(test), "better_than_baseline": brier < baseline,
        "last_date": str(x.index[-1].date()),
    }

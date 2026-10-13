"""Daily cross-asset research. Educational data, never broker instructions.

Only completed UTC dates are analyzed to avoid in-progress candles. Each
symbol has purged train / calibration / holdout periods; predictions are not
guaranteed, and model selection across a large watchlist has selection bias.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import pandas as pd
from catalog import WATCHLIST
from research_v2 import research_direction


def evaluate(close, horizon=5):
    result = research_direction(close, horizon=horizon)
    if result is None:
        return None
    return {
        "Prob. subir (estimada)": result["up_pct"],
        "Prob. descer (estimada)": result["down_pct"],
        "Acerto teste %": round(result["holdout_accuracy"] * 100, 1),
        "Brier": result["brier"],
        "Brier referência": result["baseline_brier"],
        "Validação": "Supera referência" if result["better_than_baseline"] else "Não supera referência",
        "Amostras teste": result["holdout_count"],
        "Erro calibração %": round(result["ece"] * 100, 1),
        "Sinais subida >=70 teste": result["bullish_signals"],
        "Sinais não sobrepostos >=70 teste": result["independent_bullish_signals"],
        "Acerto dos sinais >=70 %": (
            round(result["bullish_hit_rate"] * 100, 1) if result["bullish_hit_rate"] is not None else None),
        "Rentab. líquida média sinais >=70 %": (round(result["bullish_avg_net_pct"],2) if result["bullish_avg_net_pct"] is not None else None),
        "Vantagem líquida estimada %": result["expected_net_pct"],
        "Vantagem líquida conservadora %": result["conservative_net_pct"],
        "Margem de incerteza %": result["probability_haircut_pct"],
        "Limite inferior de acerto (sinais ≥70%) %": (
            round(result["bullish_wilson_lower"]*100,1)
            if result["bullish_wilson_lower"] is not None else None),
        "Acima da média de 50 velas": result["above_ma50"],
        "Aprovado para virtual": result["approved_for_paper"],
    }


def _latest_complete(raw, today):
    """Exclude today's UTC session, even if some foreign exchanges already closed.

    Conservative exclusion is deliberate: it never uses a partly formed daily
    bar for a forecast; the cost can be a one-day delay for some markets.
    """
    if raw is None or raw.empty:
        return raw
    try:
        dates = pd.DatetimeIndex(raw.index).date
        return raw.loc[dates < today].sort_index()
    except (TypeError, ValueError):
        return raw.iloc[:0]


def _atr_percent(raw):
    if not set(("Close", "High", "Low")).issubset(raw.columns) or len(raw)<30:
        return None
    c, h, l = raw["Close"], raw["High"], raw["Low"]
    tr = pd.concat([(h-l).abs(), (h-c.shift(1)).abs(), (l-c.shift(1)).abs()],axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    price = float(c.iloc[-1])
    val = 100 * atr / price if price>0 else float("nan")
    return round(val, 2) if math.isfinite(val) else None


def scan_all(progress=None, categories=None, *, downloader=None, now=None):
    if downloader is None:
        import yfinance as yf
        downloader = yf.download
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(timezone.utc).date()
    assets = WATCHLIST if categories is None else [a for a in WATCHLIST if a["category"] in categories]
    count=len(assets)
    rows=[]
    for start in range(0,count,12):
        batch=assets[start:start+12]
        symbols=[x["symbol"] for x in batch]
        try:
            data=downloader(symbols,period="2y",interval="1d",group_by="ticker",
                            auto_adjust=True,progress=False,threads=True,timeout=20)
        except Exception:
            data=pd.DataFrame()
        for asset in batch:
            symbol=asset["symbol"]
            try:
                if data is None or data.empty:
                    continue
                part = data[symbol] if isinstance(data.columns,pd.MultiIndex) else data
                part = _latest_complete(part,today)
                if part is None or len(part)<310:
                    continue
                close=part["Close"].dropna()
                if len(close)<300:
                    continue
                result=evaluate(close)
                if result is None:
                    continue
                price=float(close.iloc[-1])
                if not math.isfinite(price) or price<=0:
                    continue
                previous=float(close.iloc[-2])
                variation=100*(price/previous-1) if previous>0 else None
                rows.append({
                    "Ativo":symbol,"Mercado":asset["category"],
                    "Último fecho":round(price,4),
                    "Variação diária %":round(variation,2) if variation is not None else None,
                    "ATR 14 %":_atr_percent(part),
                    "Data":str(pd.Timestamp(close.index[-1]).date()),
                    **result,
                })
            except (KeyError,ValueError,TypeError,IndexError,OverflowError):
                continue
        if progress is not None:
            progress(min(start+len(batch),count),count)
    return pd.DataFrame(rows)

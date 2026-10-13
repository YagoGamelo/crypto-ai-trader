"""Research-only Kraken spot crypto/memecoin 30-minute studies.

Pure public market access. No private exchange credentials, no derivatives,
no leverage, no contract trading. Missing markets, spread or volume FAIL CLOSED.
Each model estimate is a direction over 4 *completed* candles, not a
guarantee of a profitable trade and not an option's success probability.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta

import pandas as pd

from catalog import CRYPTO, MEMECOINS
from research_v2 import research_direction

SUPPORTED_TIMEFRAMES = {"30m":30, "1h":60, "4h":240}
HORIZON_BARS = 4
FEE_PER_SIDE = .004
SLIPPAGE_MAJOR = .003
SLIPPAGE_MEME = .01
MIN_QUOTE_VOLUME_MAJOR = 100_000
MIN_QUOTE_VOLUME_MEME = 500_000
MAX_SPREAD_MAJOR = .008
MAX_SPREAD_MEME = .015


def _valid_number(value):
    try:
        num=float(value)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) else None


def allowed_symbol(base):
    return isinstance(base, str) and base in CRYPTO


def expected_cost_fraction(is_meme):
    return 2*(FEE_PER_SIDE + (SLIPPAGE_MEME if is_meme else SLIPPAGE_MAJOR))


def study_crypto(base, *, timeframe="30m", now=None, exchange=None):
    """Return study with quality and market-liquidity gates.

    The 'quote_volume_24h' is a backward-looking turnover proxy, NOT proof of
    instant fill liquidity. Tickers must have spot USD markets on Kraken.
    """
    if not allowed_symbol(base) or timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError("Moeda ou período não permitido")
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now deve indicar UTC")
    now=now.astimezone(timezone.utc)
    if exchange is None:
        import ccxt
        exchange=ccxt.kraken({"enableRateLimit":True,"timeout":20000})
    exchange.load_markets()
    pair=f"{base}/USD"
    market=exchange.markets.get(pair)
    if not market or not market.get("spot") or market.get("active") is False:
        raise ValueError(f"{pair}: par spot USD indisponível nesta corretora")
    raw=exchange.fetch_ohlcv(pair,timeframe=timeframe,limit=720)
    if not raw or len(raw)<330:
        raise ValueError("Histórico insuficiente de velas para modelo e validação")
    x=pd.DataFrame(raw,columns=["timestamp_ms","open","high","low","close","volume"])
    x["timestamp"]=pd.to_datetime(x["timestamp_ms"],unit="ms",utc=True)
    x=x.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    x=x[(x["timestamp"]+pd.Timedelta(minutes=SUPPORTED_TIMEFRAMES[timeframe])) <= pd.Timestamp(now)]
    x=x[(x["close"]>0)&(x["volume"]>=0)]
    if len(x)<330:
        raise ValueError("Histórico fechado insuficiente; nenhuma previsão.")
    last_timestamp=x["timestamp"].iloc[-1].to_pydatetime()
    latest_end=last_timestamp+timedelta(minutes=SUPPORTED_TIMEFRAMES[timeframe])
    age_minutes=(now-latest_end).total_seconds()/60
    max_age=max(90,2*SUPPORTED_TIMEFRAMES[timeframe])
    fresh=0<=age_minutes<=max_age
    is_meme=base in MEMECOINS
    # Daily turnover calculated from OHLCV, with a cap at available 24h bars.
    window=max(1, int(1440/SUPPORTED_TIMEFRAMES[timeframe]))
    last=x.tail(window)
    quote_volume=float((last["close"]*last["volume"]).sum())
    turnover_floor=MIN_QUOTE_VOLUME_MEME if is_meme else MIN_QUOTE_VOLUME_MAJOR
    spread=None
    try:
        ticker=exchange.fetch_ticker(pair)
        bid=_valid_number(ticker.get("bid"))
        ask=_valid_number(ticker.get("ask"))
        if bid is not None and ask is not None and ask>=bid and bid>0:
            spread=(ask-bid)/((ask+bid)/2)
    except Exception:
        pass
    spread_ceiling=MAX_SPREAD_MEME if is_meme else MAX_SPREAD_MAJOR
    liquidity_ok=(spread is not None and spread<=spread_ceiling
                  and quote_volume>=turnover_floor)
    # Virtual execution must not assume that a 50 USD wallet can trade
    # below the exchange's advertised minimum order size/notional.
    limits=market.get("limits") or {}
    minimum_cost=_valid_number((limits.get("cost") or {}).get("min"))
    minimum_amount=_valid_number((limits.get("amount") or {}).get("min"))
    budget_ceiling=5.0 if is_meme else 10.0
    nominal_price=float(x["close"].iloc[-1])
    min_order_ok=((minimum_cost is None or minimum_cost<=budget_ceiling)
                  and (minimum_amount is None or minimum_amount*nominal_price<=budget_ceiling))
    close=pd.Series(x["close"].to_numpy(dtype=float),index=x["timestamp"])
    model=research_direction(close,horizon=HORIZON_BARS,
                             round_trip_cost=expected_cost_fraction(is_meme))
    if model is None:
        raise ValueError("Modelo sem validação histórica suficiente")
    # An extreme recent one-candle return can dominate an illiquid meme market.
    recent_return=close.pct_change().tail(48)
    max_single_move=float(recent_return.abs().max())
    violent_market=max_single_move > (.12 if is_meme else .06)
    eligible=(bool(model["approved_for_paper"]) and fresh and
              liquidity_ok and min_order_ok and not violent_market)
    reasons=[]
    if not fresh: reasons.append("Preço desatualizado")
    if quote_volume<turnover_floor: reasons.append("Volume negociado baixo")
    if spread is None: reasons.append("Spread indisponível")
    elif spread>spread_ceiling: reasons.append("Spread elevado")
    if not min_order_ok: reasons.append("Mínimo de ordem superior ao orçamento virtual")
    if violent_market: reasons.append("Variação recente extrema")
    if not model["approved_for_paper"]: reasons.append("Modelo não superou filtros históricos")
    return {
        "base":base,"pair":pair,"is_meme":is_meme,"timeframe":timeframe,
        "forecast_horizon_minutes":HORIZON_BARS*SUPPORTED_TIMEFRAMES[timeframe],
        "price_usd":float(close.iloc[-1]),"last_closed_utc":latest_end.isoformat(),
        "data_age_minutes":round(age_minutes,1),
        "latest_candles":x[["timestamp","open","high","low","close","volume"]].tail(120).copy(),
        "quote_volume_24h_usd":round(quote_volume,2),
        "minimum_order_ok":min_order_ok,
        "spread_pct":round(100*spread,3) if spread is not None else None,
        "max_one_candle_move_pct":round(100*max_single_move,2),
        "fee_per_side_pct":FEE_PER_SIDE*100,
        "slippage_per_side_pct":(SLIPPAGE_MEME if is_meme else SLIPPAGE_MAJOR)*100,
        "estimated_round_trip_cost_pct":round(100*expected_cost_fraction(is_meme),2),
        "model":model,"paper_buy_eligible":eligible,
        "risk_notes":reasons,
        "market":"Kraken spot public",
    }

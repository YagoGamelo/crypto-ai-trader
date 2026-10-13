"""Portfolio-wide long-only paper trading from research table observations.

Virtual execution uses the latest historical close, not a broker executable price.
It performs ONE scan/cycle only when invoked and has no live order endpoints.
"""
from datetime import datetime, timezone
from math import isfinite

INITIAL_USD = 50.0
FEE_RATE = 0.002
MAX_ALLOCATION = 0.20
MAX_POSITIONS = 5
MIN_ORDER_USD = 2.0
RESERVE_SHARE = 0.30
ENTRY_UP = 70.0
EXIT_UP = 50.0
EXIT_DOWN = 70.0
TRAIL_START = 0.04
TRAIL_DRAWDOWN = 0.03
HARD_STOP = 0.05

def new_portfolio():
    return {"cash": INITIAL_USD, "reserved": 0.0,
            "positions": {}, "logs": [], "last_prices": {}}

def _numeric(value):
    if isinstance(value, bool):
        raise ValueError("Invalid numerical input")
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid numerical input") from exc
    if not isfinite(value):
        raise ValueError("Non-finite numerical input")
    return value

def market_signal(prob_up, validated):
    """Classify model direction, not a validated or calibrated real win rate."""
    p = _numeric(prob_up)
    if not 0 <= p <= 100:
        raise ValueError("Probability out of range")
    if p <= EXIT_UP:
        return "VENDER / FECHAR"  # includes down probability >= 70%
    if p >= ENTRY_UP and validated:
        return "COMPRAR (candidato)"
    return "ESPERAR"

def equity(state):
    return (state["cash"] + state["reserved"] +
            sum(p["units"] * state["last_prices"].get(ticker, p["entry"])
                for ticker, p in state["positions"].items()))

def _log(state, action, symbol, price, units, reason, fee=0, realized=0, reserve=0, date=None):
    state["logs"].insert(0, {
        "Hora UTC": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "Ativo": symbol, "Ação": action, "Preço USD": round(price, 5),
        "Unidades": round(units, 8), "Taxas USD": round(fee, 5),
        "P/L líquido USD": round(realized, 5),
        "Reserva USD": round(reserve, 5), "Motivo": reason,
        "Data dos preços": str(date or ""),
    })
    state["logs"] = state["logs"][:500]

def process_scan(state, frame, execute=False):
    """Evaluate all rows, sell positions before buying fresh candidates.

    Only the most recent scan values are used. The model-provided probabilities
    are uncalibrated and may be misleading. Strictly isolated paper simulation.
    """
    import pandas as pd
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Expected pandas DataFrame")
    required = {"Ativo","Mercado","Último fecho",
                "Prob. subir (estimada)","Prob. descer (estimada)",
                "Validação","Data"}
    if not required.issubset(frame.columns):
        raise ValueError("Missing scan data")
    if frame["Ativo"].duplicated().any():
        raise ValueError("Duplicate tickers in scan")
    signals=[]
    rows={}
    for record in frame.to_dict("records"):
        symbol=str(record["Ativo"])
        price=_numeric(record["Último fecho"])
        up=_numeric(record["Prob. subir (estimada)"])
        down=_numeric(record["Prob. descer (estimada)"])
        if price <= 0 or not 0 <= up <= 100 or not 0 <= down <= 100 or abs(up+down-100)>0.21:
            continue
        # Reject crypto and ETFs in this first equities-only automated simulator.
        if record["Mercado"] != "Ações":
            continue
        if not symbol or not record["Data"]:
            continue
        validated=record["Validação"]=="Supera referência"
        signal=market_signal(up,validated)
        rows[symbol]=(record,price,up,down,validated)
        state["last_prices"][symbol]=price
        signals.append({"Ativo":symbol,"Subida estimada %":up,
                        "Descida estimada %":down,"Modelo supera referência":validated,
                        "Sinal IA":signal, "Data":str(record["Data"])})
    if not execute:
        return signals, []
    actions=[]
    positions=state["positions"]
    # Exits take priority. Never force-sell because data for a held symbol is missing.
    for ticker in list(positions):
        if ticker not in rows:
            continue
        record, price, up, down, validated=rows[ticker]
        holding=positions[ticker]
        prev_peak=holding["peak"]
        holding["peak"]=max(prev_peak,price)
        reason=None
        if down >= EXIT_DOWN:
            reason="probabilidade de descida >=70%"
        elif up <= EXIT_UP:
            reason="probabilidade de subida <=50%"
        elif price <= holding["entry"]*(1-HARD_STOP):
            reason="stop de risco (-5%)"
        elif (holding["peak"]>=holding["entry"]*(1+TRAIL_START)
              and price<=holding["peak"]*(1-TRAIL_DRAWDOWN)):
            reason="stop móvel (-3% desde pico observado após +4%)"
        if reason is None:
            continue
        units=holding["units"]
        fee=price*units*FEE_RATE
        proceeds=price*units-fee
        realized=proceeds-holding["cost"]
        reserve=max(0,realized)*RESERVE_SHARE
        state["cash"]+=proceeds-reserve
        state["reserved"]+=reserve
        del positions[ticker]
        _log(state,"VENDER",ticker,price,units,reason,fee,realized,reserve,record["Data"])
        actions.append(f"VENDA {ticker}: {reason}")
    # Candidate buys are prioritized by highest upward probability.
    candidates=sorted(
        ((ticker, *values) for ticker, values in rows.items()
         if ticker not in positions and values[2]>=ENTRY_UP and values[4]),
        key=lambda x:x[3],reverse=True)
    for ticker,record,price,up,down,validated in candidates:
        if len(positions)>=MAX_POSITIONS:
            break
        # No same-ticker buy immediately after its sale in this cycle.
        if any(a.startswith(f"VENDA {ticker}:") for a in actions):
            continue
        budget=min(state["cash"],max(0,equity(state)-state["reserved"])*MAX_ALLOCATION)
        if budget<MIN_ORDER_USD:
            break
        units=budget/(price*(1+FEE_RATE))
        fee=price*units*FEE_RATE
        cost=price*units+fee
        if cost>state["cash"]+1e-7:
            continue
        state["cash"]=max(0,state["cash"]-cost)
        positions[ticker]={"units":units,"entry":price,"peak":price,
                           "cost":cost,"date":str(record["Data"])}
        reason="subida estimada >=70% e modelo supera referência"
        _log(state,"COMPRAR",ticker,price,units,reason,fee,date=record["Data"])
        actions.append(f"COMPRA {ticker}: {reason}")
    return signals, actions

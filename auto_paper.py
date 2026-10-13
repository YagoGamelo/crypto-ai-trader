"""Session-local STOCK research trader; PAPER ONLY and no broker APIs.

A 70% forecast is not 70% profitable-trade certainty. Besides calibrated
historic quality, entries need positive conservatively adjusted net edge.
Daily closing prices are used as reference; simulated entry/exit slippage
makes estimated virtual fills less optimistic, but not executable quotes.
"""
from __future__ import annotations
import math
from datetime import date, datetime, timezone
from risk_rules import budget_for_entry, entry_stop_fraction, trailing_exit

BUY_THRESHOLD = .70
SELL_THRESHOLD = .50
DOWN_SELL_THRESHOLD = .70
TRAIL_ENABLE_AFTER_GAIN = .04
TRAIL_FROM_PEAK = .03
STARTING_CASH_USD = 50.0
FEE_PER_SIDE = .002
MAX_POSITION_FRACTION = .20
MAX_POSITIONS = 3
STOP_LOSS = .05
PROFIT_RESERVE = .30
MAX_DAILY_DRAWDOWN = .05
MIN_PURCHASE_USD = 2.0
MAX_PRICE_AGE_DAYS = 4
SIMULATED_SLIPPAGE = .001
COOLDOWN_CALENDAR_DAYS = 2

def create_portfolio(starting_cash=STARTING_CASH_USD):
    if not math.isfinite(starting_cash) or starting_cash <= 0:
        raise ValueError("Saldo inicial inválido")
    return {"cash":float(starting_cash),"reserved":0.0,"positions":{},
            "trades":[],"last_evaluated":{},"last_prices":{},
            "daily_reference":None,"daily_reference_date":None,
            "last_run":None,"initial_cash":float(starting_cash),
            "peak_equity":float(starting_cash),
            "last_exit_date":{}}

def portfolio_equity(portfolio):
    return portfolio["cash"] + portfolio["reserved"] + sum(
        position["quantity"] * portfolio["last_prices"].get(ticker,position["entry_price"])
        for ticker,position in portfolio["positions"].items()
    )

def _valid_number(value):
    try:
        result=float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None

def _normalize(row, today):
    ticker=row.get("Ativo")
    if not isinstance(ticker,str) or not ticker.strip() or row.get("Mercado") != "Ações":
        return None
    price=_valid_number(row.get("Último fecho"))
    p_up=_valid_number(row.get("Prob. subir (estimada)"))
    brier=_valid_number(row.get("Brier"))
    base=_valid_number(row.get("Brier referência"))
    tested=_valid_number(row.get("Amostras teste"))
    if price is None or price <= 0 or p_up is None or not 0 <= p_up <= 100:
        return None
    try:
        day=date.fromisoformat(str(row.get("Data")))
    except ValueError:
        return None
    if not 0 <= (today-day).days <= MAX_PRICE_AGE_DAYS:
        return None
    # No approval, no explicit positive after-cost edge => no trade.
    approved = row.get("Aprovado para virtual", False)
    edge = _valid_number(row.get("Vantagem líquida conservadora %"))
    buy_eligible=(brier is not None and base is not None and tested is not None
                  and tested >= 30 and brier < base and approved is True
                  and edge is not None and edge > 0)
    atr=_valid_number(row.get("ATR 14 %"))
    return {"ticker":ticker,"price":price,"up":p_up/100.0,
            "down":1-p_up/100.0,"trading_day":day.isoformat(),
            "buy_eligible":buy_eligible,"atr_pct":atr,"net_edge_pct":edge}

def _exit_reason(position, price, up):
    """Sell in spot only when already held; never short securities."""
    if 1-up >= DOWN_SELL_THRESHOLD-1e-9:
        return "descida estimada >=70%"
    if up <= SELL_THRESHOLD:
        return "subida estimada <=50%"
    stop=position.get("stop_fraction",STOP_LOSS)
    if price <= position["entry_price"]*(1-stop):
        return f"stop de {stop*100:.1f}% (fecho diário)"
    peak=max(position.get("highest_observed",position["entry_price"]),price)
    if trailing_exit(position["entry_price"],peak,price,position.get("atr_pct")):
        return "stop móvel de lucro (ajustado à volatilidade)"
    return None

def decision_table(portfolio, rows, *, now=None):
    """UI-only preview. Does not place virtual or real orders."""
    now=now or datetime.now(timezone.utc)
    today=now.astimezone(timezone.utc).date()
    results=[]
    for row in rows:
        x=_normalize(row,today)
        if x is None:
            continue
        pos=portfolio["positions"].get(x["ticker"])
        reason=_exit_reason(pos,x["price"],x["up"]) if pos else None
        if pos:
            decision="VENDER" if reason else "MANTER"
        elif x["up"]>=BUY_THRESHOLD and x["buy_eligible"]:
            decision="COMPRAR (candidato)"
        else:
            decision="ESPERAR"
        results.append({"Ativo":x["ticker"],
                        "Subida estimada %":round(100*x["up"],1),
                        "Descida estimada %":round(100*x["down"],1),
                        "Sinal":decision,
                        "Motivo":reason or ("subida >=70% e modelo supera referência"
                                         if decision.startswith("COMPRAR") else
                                         "sem posição / sinal insuficiente"),
                        "Filtros e vantagem líquida aprovados":x["buy_eligible"],
                        "Vantagem líquida conservadora %":x["net_edge_pct"],
                        "Posição aberta":bool(pos),
                        "Data":x["trading_day"]})
    return sorted(results,key=lambda x:-x["Subida estimada %"])

def evaluate_cycle(portfolio, rows, *, now=None):
    """Evaluate daily research data. Writes to an isolated in-memory ledger ONLY.

    One decision per ticker and completed candle prevents duplicate entries on
    hourly refresh. Sells have priority. At most one new position per cycle,
    with three positions total and a 5% daily drawdown entry circuit-breaker.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("O instante de avaliação requer fuso horário")
    today=now.astimezone(timezone.utc).date()
    if portfolio["daily_reference_date"] != today.isoformat():
        portfolio["daily_reference"]=portfolio_equity(portfolio)
        portfolio["daily_reference_date"]=today.isoformat()
    signals=[x for row in rows if (x:=_normalize(row,today)) is not None]
    indexed={x["ticker"]:x for x in signals}
    new=[x for x in indexed.values()
         if portfolio["last_evaluated"].get(x["ticker"])!=x["trading_day"]]
    for x in indexed.values():
        portfolio["last_prices"][x["ticker"]]=x["price"]
    actions=[]
    for x in sorted(new,key=lambda d:d["ticker"]):
        ticker=x["ticker"]
        if ticker not in portfolio["positions"]:
            continue
        position=portfolio["positions"][ticker]
        px=x["price"]
        reason=_exit_reason(position,px,x["up"])
        position["highest_observed"]=max(position.get("highest_observed",position["entry_price"]),px)
        if not reason:
            continue
        qty=position["quantity"]
        virtual_fill=px*(1-SIMULATED_SLIPPAGE)
        gross=qty*virtual_fill
        fee=gross*FEE_PER_SIDE
        net=gross-fee
        realized=net-position["total_cost"]
        reserve=min(net,max(0.0,realized)*PROFIT_RESERVE)
        portfolio["cash"]+=net-reserve
        portfolio["reserved"]+=reserve
        del portfolio["positions"][ticker]
        portfolio["last_exit_date"][ticker]=x["trading_day"]
        event={"data":now.isoformat(),"ação":"VENDER","ativo":ticker,
               "preço":px,"preço_simulado":virtual_fill,
               "quantidade":qty,"comissão":fee,
               "lucro_realizado":realized,"lucro_reservado":reserve,
               "prob_subida":x["up"],
               "motivo":reason,
               "data_mercado":x["trading_day"]}
        actions.append(event)
        portfolio["trades"].append(event)
    ref=portfolio["daily_reference"]
    current_equity=portfolio_equity(portfolio)
    portfolio["peak_equity"]=max(portfolio.get("peak_equity",portfolio["initial_cash"]),current_equity)
    # Lifetime -15% circuit breaker blocks new buys, not protective exits.
    allowed=(ref>0 and current_equity>=ref*(1-MAX_DAILY_DRAWDOWN)
             and current_equity>=portfolio["peak_equity"]*.85)
    buy_candidates=sorted(
        (x for x in new if x["ticker"] not in portfolio["positions"]
         and x["buy_eligible"] and x["up"]>=BUY_THRESHOLD
         and (x["ticker"] not in portfolio["last_exit_date"] or
              (date.fromisoformat(x["trading_day"]) -
               date.fromisoformat(portfolio["last_exit_date"][x["ticker"]])).days >= COOLDOWN_CALENDAR_DAYS)
         and not any(event["ativo"]==x["ticker"] for event in actions)),
        # Rank by conservative expected after-cost return per unit of
        # volatility, not by the highest headline probability alone.
        key=lambda x:(-(x["net_edge_pct"]/max(2.0,x["atr_pct"] or 5.0)),
                      -x["up"],x["ticker"])
    )
    if allowed and len(portfolio["positions"])<MAX_POSITIONS:
        for x in buy_candidates[:1]:
            budget=budget_for_entry(
                portfolio["cash"],portfolio_equity(portfolio)-portfolio["reserved"],
                x.get("atr_pct"))
            if budget<MIN_PURCHASE_USD:
                break
            px=x["price"]
            virtual_fill=px*(1+SIMULATED_SLIPPAGE)
            qty=budget/(virtual_fill*(1+FEE_PER_SIDE))
            fee=qty*virtual_fill*FEE_PER_SIDE
            portfolio["cash"]-=budget
            portfolio["positions"][x["ticker"]]={
                "quantity":qty,"entry_price":virtual_fill,
                "total_cost":budget,"open_date":x["trading_day"],
                "highest_observed":px,
                "atr_pct":x.get("atr_pct"),
                "stop_fraction":entry_stop_fraction(x.get("atr_pct"))}
            event={"data":now.isoformat(),"ação":"COMPRAR",
                   "ativo":x["ticker"],"preço":px,
                   "preço_simulado":virtual_fill,
                   "quantidade":qty,"comissão":fee,
                   "lucro_realizado":0.0,"lucro_reservado":0.0,
                   "prob_subida":x["up"],
                   "motivo":"subida >=70%; teste de qualidade e vantagem líquida positiva",
                   "data_mercado":x["trading_day"]}
            actions.append(event)
            portfolio["trades"].append(event)
    for x in new:
        portfolio["last_evaluated"][x["ticker"]]=x["trading_day"]
    portfolio["last_run"]=now.isoformat()
    portfolio["trades"]=portfolio["trades"][-250:]
    return {"actions":actions,"signal_table":decision_table(portfolio,rows,now=now),
            "valid_signals":len(signals),
            "new_signals":len(new),"buy_candidates":len(buy_candidates),
            "risk_gate_open":allowed,"equity":portfolio_equity(portfolio),
            "peak_equity":portfolio["peak_equity"],
            "current_drawdown_pct":round(100*(portfolio_equity(portfolio)/portfolio["peak_equity"]-1),2),
            "positions":len(portfolio["positions"])}

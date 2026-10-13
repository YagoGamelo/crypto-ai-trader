"""Short-horizon Kraken spot PAPER wallet for BTC, crypto and memecoins.

No margin, derivatives, binary products, private keys, withdrawals or real
orders. All amounts are nominal USD and exist only in one Streamlit session.
The 70/70/50 rules work on a calibrated 4-BAR spot move forecast; estimates
are not guaranteed and market fills are simulated with a cost cushion.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from risk_rules import entry_stop_fraction, budget_for_entry, trailing_exit

STARTING_USD=50.0
BUY_UP=70.0
SELL_UP=50.0
SELL_DOWN=70.0
FEE=.004
MAX_MEME_ALLOCATION=.10
MAX_MEME_RISK=.005
RESERVE_FRACTION=.30
MIN_TRADE=2.0


def new_wallet(initial=STARTING_USD):
    if isinstance(initial,bool) or not isinstance(initial,(float,int)) or not math.isfinite(initial) or initial<=0:
        raise ValueError("Saldo inválido")
    return {"cash":float(initial),"reserved":0.0,"position":None,
            "trades":[],"last_candle":{},"initial":float(initial)}


def equity(wallet, current_price=None):
    position=wallet.get("position")
    held_value=0.0
    if position is not None:
        px=position["last_price"] if current_price is None else current_price
        if not math.isfinite(float(px)) or float(px)<=0:
            raise ValueError("Preço de carteira inválido")
        held_value=position["quantity"]*float(px)
    return wallet["cash"]+wallet["reserved"]+held_value


def decision(wallet, study, *, execute=False):
    """One action per closed candle, buy/sell only for selected crypto.

    Exit decisions still work when the model is no longer eligible for new
    buys, provided the selected public-market quote is fresh. The user must
    select an existing holding to review its exit; unattended 24/7 execution
    is NOT implemented.
    """
    model=study.get("model") or {}
    pair=study.get("pair")
    price=study.get("price_usd")
    ts=study.get("last_closed_utc")
    if not isinstance(pair,str) or not isinstance(ts,str) or not ts:
        raise ValueError("Dados de mercado incompletos")
    if isinstance(price,bool) or not isinstance(price,(int,float)) or not math.isfinite(price) or price<=0:
        raise ValueError("Preço de mercado inválido")
    up=model.get("up_pct")
    down=model.get("down_pct")
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (up,down)):
        raise ValueError("Probabilidades inválidas")
    if not (0<=up<=100 and 0<=down<=100 and abs(up+down-100)<=.21):
        raise ValueError("Probabilidades inconsistentes")
    position=wallet.get("position")
    same_asset=position is not None and position["pair"]==pair
    if position and not same_asset:
        return "MANTER — existe uma posição noutro ativo; seleciona-a primeiro"
    if wallet.get("last_candle",{}).get(pair)==ts:
        return "ESPERAR — esta vela já foi avaliada"
    if study.get("data_age_minutes",float("inf"))>max(90,
              2*({"30m":30,"1h":60,"4h":240}.get(study.get("timeframe"),30))):
        return "PAUSADO — preço desatualizado"
    if position:
        peak=max(position["peak"],price)
        stop=entry_stop_fraction(position.get("atr_pct"))
        reason=None
        if down>=SELL_DOWN:
            reason="queda estimada >=70%"
        elif up<=SELL_UP:
            reason="subida estimada <=50%"
        elif price <= position["entry"]*(1-stop):
            reason="stop de risco virtual"
        elif trailing_exit(position["entry"],peak,price,position.get("atr_pct")):
            reason="stop móvel virtual"
        elif (datetime.fromisoformat(ts)-datetime.fromisoformat(position["entered_at"])).total_seconds() >= (24 if position["is_meme"] else 72)*3600:
            reason="tempo máximo de observação excedido"
        if not execute:
            return f"VENDER (candidato): {reason}" if reason else "MANTER"
        wallet["last_candle"][pair]=ts
        position["last_price"]=price
        position["peak"]=peak
        if reason:
            fee=position["quantity"]*price*FEE
            slip=study.get("slippage_per_side_pct",.3)/100
            simulated_fill=price*(1-slip)
            fee=position["quantity"]*simulated_fill*FEE
            proceeds=position["quantity"]*simulated_fill-fee
            net=proceeds-position["spent"]
            reserve=min(proceeds,max(0.0,net)*RESERVE_FRACTION)
            wallet["cash"]+=proceeds-reserve
            wallet["reserved"]+=reserve
            wallet["position"]=None
            wallet["trades"].insert(0,{
                "UTC":ts,"Moeda":pair,"Ação":"VENDER","Preço observado":price,
                "Preço simulado":round(simulated_fill,9),
                "Unidades":position["quantity"],"P/L USD":round(net,5),
                "Comissão USD":round(fee,5),"Reserva USD":round(reserve,5),
                "Motivo":reason})
            return f"VENDA VIRTUAL {pair}: {reason} | resultado líquido {net:+.2f} USD"
        return "MANTER — posição aberta; sem saída válida"
    if up>=BUY_UP and study.get("paper_buy_eligible") and model.get("approved_for_paper"):
        if not execute:
            return "COMPRAR (candidato virtual) — subida >=70% e filtros aprovados"
        is_meme=bool(study.get("is_meme"))
        free_equity=wallet["cash"]
        # Memes may move >stop on one tick: apply stricter budgets.
        if is_meme:
            risk_frac=MAX_MEME_RISK
            alloc=MAX_MEME_ALLOCATION
        else:
            risk_frac=.01
            alloc=.20
        stop=entry_stop_fraction(None)
        budget=min(free_equity,free_equity*alloc,free_equity*risk_frac/stop)
        if budget<MIN_TRADE:
            return "ESPERAR — orçamento pequeno demais"
        slip=study.get("slippage_per_side_pct",1 if is_meme else .3)/100
        fill=price*(1+slip)
        qty=budget/(fill*(1+FEE))
        fee=qty*fill*FEE
        wallet["cash"]-=budget
        wallet["position"]={
            "pair":pair,"quantity":qty,"entry":fill,"last_price":price,
            "peak":fill,"spent":budget,"entered_at":ts,
            "is_meme":is_meme,"atr_pct":None}
        wallet["last_candle"][pair]=ts
        wallet["trades"].insert(0,{
            "UTC":ts,"Moeda":pair,"Ação":"COMPRAR",
            "Preço observado":price,"Preço simulado":round(fill,9),
            "Unidades":qty,"P/L USD":0.0,"Comissão USD":round(fee,5),
            "Reserva USD":0.0,"Motivo":"subida >=70% + testes e liquidez"})
        return f"COMPRA VIRTUAL {pair}: {budget:.2f} USD em spot"
    if execute:
        wallet["last_candle"][pair]=ts
    return "ESPERAR — probabilidade, risco ou liquidez insuficientes"

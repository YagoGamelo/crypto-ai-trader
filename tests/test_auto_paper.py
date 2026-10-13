"""Offline checks for 70% buy, 50% sell; never contact trading brokers."""
from datetime import datetime, timezone, timedelta
import pytest
from auto_paper import create_portfolio, evaluate_cycle, portfolio_equity

CLOCK = datetime(2026,10,13,17,0,tzinfo=timezone.utc)

def row(ticker="MSFT",p=70,price=100,when="2026-10-13",valid=True):
    return {"Ativo":ticker,"Mercado":"Ações","Último fecho":price,
            "Prob. subir (estimada)":p,"Brier":.16 if valid else .25,
            "Brier referência":.20,"Amostras teste":100,"Data":when}

def test_buy_exactly_70_and_hold_above_50():
    p=create_portfolio()
    result=evaluate_cycle(p,[row(p=70)],now=CLOCK)
    assert result["actions"][0]["ação"]=="COMPRAR"
    assert "MSFT" in p["positions"]
    result=evaluate_cycle(p,[row(p=50.1,when="2026-10-14")],now=CLOCK+timedelta(days=1))
    assert not result["actions"]
    assert "MSFT" in p["positions"]

def test_sell_exactly_50_and_reserve_30_percent_net_gain():
    p=create_portfolio()
    evaluate_cycle(p,[row()],now=CLOCK)
    result=evaluate_cycle(p,[row(p=50,price=120,when="2026-10-14")],now=CLOCK+timedelta(days=1))
    action=result["actions"][0]
    assert action["ação"]=="VENDER"
    assert p["reserved"]==pytest.approx(action["lucro_realizado"]*.30)
    assert portfolio_equity(p)>50

def test_no_buy_below_70_or_failed_validation():
    p=create_portfolio()
    result=evaluate_cycle(p,[row("AAPL",p=69.9),row("MSFT",p=90,valid=False)],now=CLOCK)
    assert not result["actions"]
    assert p["cash"]==50

def test_5_percent_daily_stop_overrides_high_probability():
    p=create_portfolio()
    evaluate_cycle(p,[row(p=80)],now=CLOCK)
    result=evaluate_cycle(p,[row(p=90,price=94,when="2026-10-14")],now=CLOCK+timedelta(days=1))
    assert result["actions"][0]["ação"]=="VENDER"
    assert "stop" in result["actions"][0]["motivo"]
    assert p["reserved"]==0

def test_does_not_duplicate_same_day_decisions():
    p=create_portfolio()
    evaluate_cycle(p,[row(p=75)],now=CLOCK)
    result=evaluate_cycle(p,[row(p=75)],now=CLOCK+timedelta(minutes=5))
    assert result["actions"]==[]
    assert len(p["trades"])==1

def test_only_one_buy_per_cycle_max_three_positions():
    p=create_portfolio()
    rows=[row("STOCK"+str(i),p=75+i) for i in range(5)]
    result=evaluate_cycle(p,rows,now=CLOCK)
    assert len(result["actions"])==1
    for d in range(1,5):
        instant=CLOCK+timedelta(days=d)
        current=[dict(r, Data=instant.date().isoformat()) for r in rows]
        evaluate_cycle(p,current,now=instant)
    assert len(p["positions"])==3
    assert p["cash"]>=0

def test_invalid_stale_or_nonstock_quotes_rejected():
    p=create_portfolio()
    candidates=[row(when="2026-08-01"),dict(row(),Mercado="ETF"),row(price=0),row(p=101)]
    result=evaluate_cycle(p,candidates,now=CLOCK)
    assert result["valid_signals"]==0
    assert result["actions"]==[]

def test_sell_on_50_even_if_validation_degrades():
    p=create_portfolio()
    evaluate_cycle(p,[row()],now=CLOCK)
    result=evaluate_cycle(p,[row(p=49,valid=False,when="2026-10-14")],now=CLOCK+timedelta(days=1))
    assert result["actions"][0]["ação"]=="VENDER"

def test_circuit_breaker_blocks_new_buys():
    p=create_portfolio()
    evaluate_cycle(p,[row(p=80)],now=CLOCK)
    p["daily_reference"]=100.0
    result=evaluate_cycle(p,[row("AAPL",p=90)],now=CLOCK)
    assert result["risk_gate_open"] is False
    assert not result["actions"]

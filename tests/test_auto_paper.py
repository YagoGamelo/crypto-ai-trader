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

def test_70_percent_down_is_explicit_sell_reason():
    p=create_portfolio()
    evaluate_cycle(p,[row(p=70)],now=CLOCK)
    result=evaluate_cycle(p,[row(p=30,price=110,when="2026-10-14")],
                          now=CLOCK+timedelta(days=1))
    assert result["actions"][0]["ação"]=="VENDER"
    assert "descida estimada >=70%" in result["actions"][0]["motivo"]

def test_trailing_exit_after_profitable_peak():
    p=create_portfolio()
    evaluate_cycle(p,[row(p=80,price=100)],now=CLOCK)
    evaluate_cycle(p,[row(p=80,price=110,when="2026-10-14")],
                   now=CLOCK+timedelta(days=1))
    result=evaluate_cycle(p,[row(p=65,price=106,when="2026-10-15")],
                          now=CLOCK+timedelta(days=2))
    assert result["actions"][0]["ação"]=="VENDER"
    assert "stop móvel" in result["actions"][0]["motivo"]
    assert p["reserved"]>0

def test_decision_table_shows_both_directions_without_orders():
    from auto_paper import decision_table
    p=create_portfolio()
    records=[row("AAPL",p=71),row("MSFT",p=29)]
    signals=decision_table(p,records,now=CLOCK)
    assert {x["Ativo"]:x["Sinal"] for x in signals}=={
        "AAPL":"COMPRAR (candidato)","MSFT":"ESPERAR"}
    assert p["positions"]=={}
    assert all(x["Descida estimada %"]==100-x["Subida estimada %"]
               for x in signals)

def test_no_shorts_when_down_prediction_high():
    p=create_portfolio()
    result=evaluate_cycle(p,[row(p=20)],now=CLOCK)
    assert result["actions"]==[]
    assert p["positions"]=={}

def test_new_calibrated_research_must_approve_buy():
    p=create_portfolio()
    candidate=dict(row("AAPL",p=95), **{"Aprovado para virtual":False, "ATR 14 %":2.5})
    result=evaluate_cycle(p,[candidate],now=CLOCK)
    assert result["actions"]==[]
    assert "AAPL" not in p["positions"]

def test_atr_sizing_reduces_position_in_volatile_stock():
    low=create_portfolio()
    high=create_portfolio()
    first=dict(row("LOW",p=80), **{"Aprovado para virtual":True,"ATR 14 %":1})
    second=dict(row("HIGH",p=80), **{"Aprovado para virtual":True,"ATR 14 %":7})
    evaluate_cycle(low,[first],now=CLOCK)
    evaluate_cycle(high,[second],now=CLOCK)
    low_cost=low["positions"]["LOW"]["total_cost"]
    high_cost=high["positions"]["HIGH"]["total_cost"]
    assert high_cost<low_cost
    assert low_cost<=50*.2+1e-7
    assert high["positions"]["HIGH"]["stop_fraction"]==pytest.approx(.08)

def test_lifetime_drawdown_prevents_new_entries_but_not_exits():
    p=create_portfolio()
    evaluate_cycle(p,[row("AAPL",p=75)],now=CLOCK)
    # Simulate a previous higher equity peak, without borrowing funds.
    p["peak_equity"]=100.
    next_day=CLOCK+timedelta(days=1)
    result=evaluate_cycle(p,[row("MSFT",p=85,when="2026-10-14")],now=next_day)
    assert result["risk_gate_open"] is False
    assert "MSFT" not in p["positions"]

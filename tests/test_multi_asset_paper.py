"""Offline tests for 70/70/50 strategy; no network or broker calls."""
import pandas as pd
import pytest
from multi_asset_paper import (
    new_portfolio, market_signal, process_scan, equity,
    ENTRY_UP, EXIT_UP, EXIT_DOWN,
)

def table(records):
    return pd.DataFrame([{
        "Ativo": ticker, "Mercado": market, "Último fecho": price,
        "Prob. subir (estimada)": up, "Prob. descer (estimada)": 100-up,
        "Validação": "Supera referência" if validated else "Não supera referência",
        "Data": "2026-10-13",
    } for ticker, market, price, up, validated in records])

def test_thresholds():
    assert ENTRY_UP == 70
    assert EXIT_UP == 50
    assert EXIT_DOWN == 70
    assert market_signal(70, True) == "COMPRAR (candidato)"
    assert market_signal(69.9, True) == "ESPERAR"
    assert market_signal(70, False) == "ESPERAR"
    assert market_signal(50, True) == "VENDER / FECHAR"
    assert market_signal(30, True) == "VENDER / FECHAR"

def test_buy_only_on_validated_up_70():
    state = new_portfolio()
    _, actions = process_scan(state, table([
        ("AAPL", "Ações", 100, 75, True),
        ("MSFT", "Ações", 100, 90, False),
        ("ETH-USD", "Cripto", 100, 95, True),
        ("NVDA", "Ações", 100, 69, True),
    ]), execute=True)
    assert len(actions) == 1
    assert "AAPL" in state["positions"]
    assert "MSFT" not in state["positions"]
    assert state["cash"] == pytest.approx(40)
    assert equity(state) < 50  # simulated entry fee
    assert state["reserved"] == 0

def test_close_at_50_and_reserve_profit():
    state = new_portfolio()
    process_scan(state, table([("AAPL", "Ações", 100, 75, True)]), execute=True)
    _, actions = process_scan(state, table([("AAPL", "Ações", 110, 50, True)]), execute=True)
    assert actions and "VENDA AAPL" in actions[0]
    assert state["positions"] == {}
    assert state["reserved"] > 0
    assert equity(state) > 50

def test_down_70_also_exits():
    state = new_portfolio()
    process_scan(state, table([("AAPL", "Ações", 100, 74, True)]), execute=True)
    _, actions = process_scan(state, table([("AAPL", "Ações", 110, 30, False)]), execute=True)
    assert "VENDA AAPL" in actions[0]
    assert "descida >=70" in actions[0]

def test_trailing_stop_without_fixed_probability_exit():
    state = new_portfolio()
    process_scan(state, table([("AAPL", "Ações", 100, 75, True)]), execute=True)
    process_scan(state, table([("AAPL", "Ações", 110, 75, True)]), execute=True)
    _, actions = process_scan(state, table([("AAPL", "Ações", 106, 65, True)]), execute=True)
    assert actions and "stop móvel" in actions[0]
    assert state["reserved"] > 0

def test_missing_assets_are_not_liquidated():
    state = new_portfolio()
    process_scan(state, table([("AAPL", "Ações", 100, 75, True)]), execute=True)
    _, actions = process_scan(state, table([("MSFT", "Ações", 100, 20, True)]), execute=True)
    assert not actions
    assert "AAPL" in state["positions"]

def test_repeated_scan_does_not_duplicate_position():
    state=new_portfolio()
    data=table([("AAPL","Ações",100,72,True)])
    process_scan(state,data,execute=True)
    _,actions=process_scan(state,data,execute=True)
    assert actions==[]
    assert len(state["positions"])==1

def test_dry_run_no_orders():
    state=new_portfolio()
    signals,actions=process_scan(state,table([("AAPL","Ações",100,80,True)]),execute=False)
    assert actions==[]
    assert signals[0]["Sinal IA"]=="COMPRAR (candidato)"
    assert state["positions"]=={}

def test_limit_five_positions_and_no_negative_cash():
    state=new_portfolio()
    process_scan(state,table([
        (f"TEST{i}","Ações",100,90-i,True) for i in range(12)]),execute=True)
    assert len(state["positions"])<=5
    assert state["cash"]>=0
    assert state["reserved"]>=0

@pytest.mark.parametrize("bad",[-1,101,float("nan"),float("inf")])
def test_bad_probability(bad):
    with pytest.raises(ValueError):
        market_signal(bad,True)

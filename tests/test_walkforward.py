"""Offline backtest tests use synthetic market price data."""
import numpy as np
import pandas as pd
import pytest
from walkforward import backtest_one_asset

def test_backtest_next_open_and_costs():
    rng=np.random.default_rng(5)
    prices=100*np.exp(np.cumsum(rng.normal(.0007,.014,420)))
    frame=pd.DataFrame({"Open":prices*1.0004,"Close":prices,
                        "High":prices*1.008,"Low":prices*.992},
                        index=pd.bdate_range("2024-01-01",periods=420))
    result=backtest_one_asset(frame,retrain_every=12)
    assert result["bars_tested"]==100
    assert result["annualized_pct"] is None
    assert result["completed_trades"]>=0
    assert 0<=result["invested_days_pct"]<=100
    assert len(result["equity_curve"])==100
    assert result["max_drawdown_pct"]<=0
    assert abs(result["return_pct"])<100

def test_insufficient_history_rejected():
    with pytest.raises(ValueError):
        backtest_one_asset(pd.DataFrame({"Open":[1]*40,"Close":[1]*40}))

def test_forecaster_never_sees_price_on_its_execution_day(monkeypatch):
    import walkforward
    observed_sizes=[]
    def fake_forecast(past_close,horizon):
        observed_sizes.append(len(past_close))
        return None  # intentionally no signal / no trades
    monkeypatch.setattr(walkforward,"research_direction",fake_forecast)
    frame=pd.DataFrame({"Open":[100.0]*355,"Close":[100.0]*355})
    result=backtest_one_asset(frame,start_bars=320)
    assert observed_sizes
    assert observed_sizes[0]==320
    assert max(observed_sizes)==354
    assert result["return_pct"]==0
    assert result["completed_trades"]==0

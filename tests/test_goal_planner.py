"""Pure mathematical checks: 400% is a target, NOT a forecast."""
import math
import pytest

from goal_planner import calculate_goal, compound_path, summarize_closed_trades


def test_four_hundred_percent_goal_from_fifty():
    result=calculate_goal(50,50,400,12)
    assert result["target_capital"] == 250
    assert result["profit_goal"] == 200
    assert result["current_return_pct"] == 0
    assert result["remaining_to_target"] == 200
    assert result["goal_progress_pct"] == 0
    assert result["monthly_growth_needed_pct"] == pytest.approx((5**(1/12)-1)*100,abs=.001)
    assert not result["reached"]


def test_goal_reached_and_downside():
    achieved=calculate_goal(50,250,400,12)
    assert achieved["reached"]
    assert achieved["goal_progress_pct"] == 100
    assert achieved["monthly_growth_needed_pct"] == 0
    losing=calculate_goal(50,25,400,12)
    assert losing["goal_progress_pct"] == 0
    assert losing["current_return_pct"] == -50
    assert losing["monthly_growth_needed_pct"] > 14


def test_compounding_is_illustration_only():
    path=compound_path(50,(5**(1/12)-1)*100,12)
    assert len(path) == 13
    assert path[0] == 50
    assert path[-1] == pytest.approx(250,abs=.01)
    decline=compound_path(50,-5,12)
    assert decline[-1] < 50


def test_wallet_closed_trades_do_not_include_open_buys():
    events=[
        {"ação":"COMPRAR","lucro_realizado":0},
        {"ação":"VENDER","lucro_realizado":2.5},
        {"ação":"VENDER","lucro_realizado":-1.5},
    ]
    stats=summarize_closed_trades(events)
    assert stats["trades"] == 2
    assert stats["wins"] == 1
    assert stats["losses_or_zero"] == 1
    assert stats["win_rate_pct"] == 50
    assert stats["net_realized"] == 1
    assert not stats["enough_for_preliminary_review"]
    assert summarize_closed_trades([{"ação":"VENDER","lucro_realizado":float("nan")}])["trades"] == 0


@pytest.mark.parametrize("invalid",[0,-1,float("nan"),float("inf"),True])
def test_invalid_initial_capital_rejected(invalid):
    with pytest.raises(ValueError):
        calculate_goal(invalid,50)


@pytest.mark.parametrize("invalid",[-1,float("nan"),float("inf"),True])
def test_invalid_current_capital_rejected(invalid):
    with pytest.raises(ValueError):
        calculate_goal(50,invalid)


def test_zero_balance_is_not_a_compounding_opportunity():
    result=calculate_goal(50,0,400,12)
    assert result["current_return_pct"]==-100
    assert result["goal_progress_pct"]==0
    assert result["monthly_growth_needed_pct"] is None
    assert result["remaining_to_target"]==250


def test_no_unreasonable_monthly_rates():
    for bad in (-100, float("nan"),float("inf")):
        with pytest.raises(ValueError):
            compound_path(50,bad)

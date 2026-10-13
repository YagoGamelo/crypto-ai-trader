import pytest
from strategy_scorecard import audit_backtest


def sample(**overrides):
    record={"return_pct":24.0, "max_drawdown_pct":-8.0,
            "bars_tested":350,"completed_trades":35,
            "total_fees_usd":3.5}
    record.update(overrides)
    return record


def test_pass_does_not_authorize_real_money_or_promise_400():
    verdict=audit_backtest(sample())
    assert verdict["further_research_candidate"]
    assert verdict["result"]=="CANDIDATO A NOVOS TESTES"
    assert verdict["goal_400_annual_verified"] is False
    assert verdict["live_trading_allowed"] is False


@pytest.mark.parametrize("updates,reason_fragment",[
    ({"bars_tested":120},"252 sessões"),
    ({"completed_trades":2},"30 operações"),
    ({"return_pct":-3},"não positiva"),
    ({"max_drawdown_pct":-21},"15%"),
])
def test_poor_or_insufficient_results_are_not_approved(updates,reason_fragment):
    verdict=audit_backtest(sample(**updates))
    assert not verdict["further_research_candidate"]
    assert any(reason_fragment in reason for reason in verdict["reasons"])


@pytest.mark.parametrize("updates",[
    {"bars_tested":float("nan")},
    {"max_drawdown_pct":1},
    {"total_fees_usd":-1},
])
def test_invalid_scorecard_inputs_rejected(updates):
    with pytest.raises(ValueError):
        audit_backtest(sample(**updates))


def test_missing_information_fails():
    with pytest.raises(ValueError):
        audit_backtest({"return_pct":10})

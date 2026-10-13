"""Unit tests for expiry-only LONG options. No live price feeds."""
import pytest

from options_payoff import LongOption


def test_reality_income_example_long_call():
    example=LongOption("CALL",strike=55,premium_per_unit=.30,
                       multiplier=100,contracts=1)
    assert example.debit==pytest.approx(30)
    assert example.max_loss==pytest.approx(-30)
    assert example.breakeven==pytest.approx(55.30)
    assert example.max_gain is None
    assert example.payout(54.69)==pytest.approx(-30)
    assert example.payout(55.30)==pytest.approx(0)
    assert example.payout(60)==pytest.approx(470)


def test_long_put_loses_only_premium_and_profits_when_falling():
    option=LongOption("PUT",strike=55,premium_per_unit=1,
                      multiplier=100,contracts=1,commission_total=2)
    assert option.max_loss==-102
    assert option.breakeven==pytest.approx(53.98)
    assert option.max_gain==pytest.approx(5398)
    assert option.payout(0)==pytest.approx(5398)
    assert option.payout(100)==pytest.approx(-102)
    assert option.payout(53.98)==pytest.approx(0)


def test_call_and_put_charts_show_payoff_not_spot_forecast():
    for side in ("CALL","PUT"):
        option=LongOption(side,strike=100,premium_per_unit=3,multiplier=1)
        x,y=option.chart(current_price=110)
        assert len(x)==len(y)==121
        assert min(y)>=option.max_loss-1e-8
        assert x[0]>=0
        assert x[-1]>110


@pytest.mark.parametrize("kwargs",[
    {"kind":"SHORT_CALL","strike":50,"premium_per_unit":1},
    {"kind":"CALL","strike":0,"premium_per_unit":1},
    {"kind":"CALL","strike":55,"premium_per_unit":0},
    {"kind":"PUT","strike":55,"premium_per_unit":1,"contracts":-1},
    {"kind":"PUT","strike":55,"premium_per_unit":1,"commission_total":float("nan")},
])
def test_invalid_or_naked_options_not_supported(kwargs):
    with pytest.raises(ValueError):
        LongOption(**kwargs)


@pytest.mark.parametrize("bad",[-1,float("nan"),float("inf")])
def test_invalid_expiry_price_rejected(bad):
    with pytest.raises(ValueError):
        LongOption("CALL",55,.3).payout(bad)

"""Paper-wallet accounting: never touches real exchanges."""
import math
import pytest
from paper import connect, snapshot, step, history

def test_private_connections_start_independently():
    a, b = connect(":memory:"), connect(":memory:")
    assert step(a, 100, 0.9, enabled=True).startswith("BUY")
    assert snapshot(a, 100)["units"] > 0
    assert snapshot(b, 100)["units"] == 0
    assert snapshot(b, 100)["equity"] == 50

def test_reserve_30_percent_of_realized_net_profit():
    db = connect(":memory:")
    assert step(db, 100, .85).startswith("BUY")
    bought = snapshot(db, 100)
    quantity = bought["units"]
    assert step(db, 110, .60).startswith("SELL")
    sold = snapshot(db, 110)
    expected_net = quantity * 110 * (1-.002) - quantity*100*(1+.002)
    assert sold["reserved"] == pytest.approx(expected_net * .30)
    assert sold["units"] == 0
    assert sold["equity"] == pytest.approx(50+expected_net)
    assert "SELL" in history(db)[0][1]

def test_losses_never_create_a_profit_reserve():
    db = connect(":memory:")
    step(db, 100, .9)
    step(db, 95, .9)
    assert snapshot(db, 95)["reserved"] == 0

@pytest.mark.parametrize("bad",[-5,0,float("nan"),float("inf")])
def test_bad_prices_are_rejected(bad):
    db=connect(":memory:")
    with pytest.raises(ValueError):
        step(db, bad, .8)

@pytest.mark.parametrize("bad",[-.1,1.1,float("nan"),float("inf")])
def test_bad_probabilities_are_rejected(bad):
    db=connect(":memory:")
    with pytest.raises(ValueError):
        step(db, 100, bad)

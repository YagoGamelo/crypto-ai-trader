import pytest
from risk_rules import entry_stop_fraction,budget_for_entry,trailing_exit

def test_atr_stops_and_position_sizing():
    assert entry_stop_fraction(1)==.03
    assert entry_stop_fraction(9)==.08
    assert entry_stop_fraction(None)==.05
    assert budget_for_entry(50,50,1)==10
    assert budget_for_entry(50,50,7)==6.25
    assert budget_for_entry(3,50,7)==3

def test_invalid_account_not_allowed():
    for value in (-1,float("nan"),float("inf")):
        with pytest.raises(ValueError):
            budget_for_entry(value,50)

def test_trailing_exit_keeps_winners_longer():
    assert not trailing_exit(100,102,100)
    assert trailing_exit(100,110,106)
    assert not trailing_exit(100,110,107)
    assert not trailing_exit(100,110,106,5)

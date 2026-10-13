"""Offline, deterministic unit checks for conservative after-cost edge."""
import pytest
from edge_filter import evaluate_edge, wilson_lower_bound


def test_high_win_rate_on_two_trades_is_not_statistically_strong():
    assert wilson_lower_bound(2, 2) < .5
    assert wilson_lower_bound(11, 12) > .5
    assert wilson_lower_bound(0, 20) == 0


def test_nominal_positive_can_still_fail_under_model_uncertainty():
    edge=evaluate_edge(
        p_up=.70, avg_up=.04, avg_down=-.055,
        round_trip_cost=.006, calibration_error=.11
    )
    assert edge["expected_net_fraction"] > 0
    assert edge["conservative_net_fraction"] < 0
    assert edge["after_cost_positive"] is False
    assert edge["probability_after_haircut"] == pytest.approx(.59)


def test_stronger_upside_can_survive_costs():
    edge=evaluate_edge(.85, .10, -.02, .01, .05)
    assert edge["after_cost_positive"]
    assert edge["conservative_net_fraction"] < edge["expected_net_fraction"]
    assert edge["uncertainty_haircut"] == .08


def test_fees_can_remove_the_edge():
    cheap=evaluate_edge(.78, .06, -.04, .001, .02)
    expensive=evaluate_edge(.78, .06, -.04, .035, .02)
    assert cheap["conservative_net_fraction"] > expensive["conservative_net_fraction"]


@pytest.mark.parametrize("prob,up,down,cost,ece", [
    (float("nan"),.02,-.03,.006,.05),
    (.7,-.01,-.03,.006,.05),
    (.7,.02,.01,.006,.05),
    (.7,.02,-.03,-.05,.05),
    (.7,.02,-.03,.006,1.5),
    (1.2,.02,-.03,.006,.05),
])
def test_invalid_edge_inputs_fail_closed(prob,up,down,cost,ece):
    with pytest.raises(ValueError):
        evaluate_edge(prob,up,down,cost,ece)


def test_invalid_binomial_inputs_rejected():
    for wins,trials in [(9,8),(-1,10),(0,0)]:
        with pytest.raises(ValueError):
            wilson_lower_bound(wins,trials)

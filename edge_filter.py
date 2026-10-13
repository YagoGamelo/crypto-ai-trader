"""Conservative *research* edge estimates. Never authorize real orders.

Combines a direction probability with historical conditional move sizes and
explicit round-trip costs. These are fragile estimates under regime change:
passing the filter is only permission for PAPER research, never a profit claim.
"""
from __future__ import annotations

import math


def _finite(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def wilson_lower_bound(wins, trials, z=1.645):
    """Approximate one-sided 95% binomial lower bound, not a guarantee."""
    n = _finite(trials, "trials")
    k = _finite(wins, "wins")
    critical = _finite(z, "z")
    if n <= 0 or k < 0 or k > n or critical <= 0:
        raise ValueError("invalid binomial observations")
    p = k / n
    denom = 1 + critical * critical / n
    center = p + critical * critical / (2 * n)
    half = critical * math.sqrt(p * (1 - p) / n + critical * critical / (4 * n * n))
    return max(0., min(1., (center - half) / denom))


def evaluate_edge(p_up, avg_up, avg_down, round_trip_cost,
                  calibration_error, *, uncertainty_floor=0.08):
    """Expected trade return estimate with a DOWNWARD bias on p(up).

    Assumes conditional move magnitudes stay comparable to a held-out test,
    which can be wrong. Costs include both sides. Conservative adjustment
    always favours a smaller upside probability.
    """
    p = _finite(p_up, "p_up")
    win = _finite(avg_up, "avg_up")
    loss = _finite(avg_down, "avg_down")
    cost = _finite(round_trip_cost, "round_trip_cost")
    calibration = _finite(calibration_error, "calibration_error")
    if not (0 <= p <= 1 and win > 0 and loss <= 0
            and 0 <= cost <= .2 and 0 <= calibration <= 1
            and 0 <= uncertainty_floor <= .5):
        raise ValueError("edge assumptions outside supported range")
    haircut = max(uncertainty_floor, calibration)
    p_safe = max(0., p - haircut)
    nominal = p * win + (1-p) * loss - cost
    conservative = p_safe * win + (1-p_safe) * loss - cost
    return {
        "expected_net_fraction": nominal,
        "conservative_net_fraction": conservative,
        "probability_after_haircut": p_safe,
        "uncertainty_haircut": haircut,
        "after_cost_positive": conservative > 0,
    }

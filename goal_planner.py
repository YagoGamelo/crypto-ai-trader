"""A transparent 400%-annual-goal planner: arithmetic, NOT a trading forecast.

Functions never issue orders, choose leverage, or infer future returns from
uncalibrated model probabilities.
"""
from __future__ import annotations

import math

DEFAULT_GOAL_GAIN_PCT = 400.0


def _positive(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label}: invalid amount")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid amount") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{label}: must be finite and positive")
    return number


def calculate_goal(initial_capital, current_capital, target_gain_pct=400.0,
                   remaining_months=12):
    """Compute a target and required growth rate, never a success probability.

    '400% gain' means final wealth is five times the initial value.
    Initial and current amounts MUST be denominated in the same currency.
    """
    initial = _positive(initial_capital, "capital inicial")
    current = _positive(current_capital, "capital atual")
    if isinstance(target_gain_pct, bool):
        raise ValueError("invalid target")
    gain = float(target_gain_pct)
    if not math.isfinite(gain) or not 0 <= gain <= 10000:
        raise ValueError("invalid gain target")
    if isinstance(remaining_months, bool) or not isinstance(remaining_months, int) or not 1 <= remaining_months <= 120:
        raise ValueError("remaining_months must be 1..120")
    final_goal = initial * (1 + gain / 100)
    monthly_needed = (final_goal / current) ** (1 / remaining_months) - 1
    progress = ((current - initial) / (final_goal - initial)
                if final_goal > initial else float(current >= initial))
    return {
        "initial": round(initial, 4),
        "current": round(current, 4),
        "target_gain_pct": round(gain, 2),
        "target_capital": round(final_goal, 4),
        "profit_goal": round(final_goal - initial, 4),
        "current_return_pct": round(100 * (current / initial - 1), 3),
        "remaining_to_target": round(max(0, final_goal - current), 4),
        "goal_progress_pct": round(max(0, min(100, progress * 100)), 2),
        "monthly_growth_needed_pct": round(monthly_needed * 100, 3),
        "months": remaining_months,
        "reached": current >= final_goal,
    }


def compound_path(start, monthly_rate_pct, months=12):
    """Hypothetical constant monthly rate. Excludes costs, tax, and risk."""
    initial = _positive(start, "capital")
    if isinstance(monthly_rate_pct, bool):
        raise ValueError("invalid monthly return")
    rate = float(monthly_rate_pct) / 100
    if not math.isfinite(rate) or rate <= -1 or rate > 10:
        raise ValueError("monthly rate out of supported range")
    if isinstance(months, bool) or not isinstance(months, int) or not 1 <= months <= 120:
        raise ValueError("months must be 1..120")
    return [round(initial * (1 + rate) ** month, 4) for month in range(months + 1)]


def summarize_closed_trades(events):
    """Descriptive closed-trade information, without an unreliable annual forecast."""
    profits = []
    for event in events:
        if event.get("ação") != "VENDER":
            continue
        value = event.get("lucro_realizado")
        if isinstance(value, bool):
            continue
        try:
            pnl = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(pnl):
            profits.append(pnl)
    wins = sum(pnl > 0 for pnl in profits)
    losses = sum(pnl <= 0 for pnl in profits)
    return {
        "trades": len(profits),
        "wins": wins,
        "losses_or_zero": losses,
        "win_rate_pct": round(100 * wins / len(profits), 2) if profits else None,
        "net_realized": round(sum(profits), 4),
        "avg_win": round(sum(x for x in profits if x > 0) / wins, 4) if wins else None,
        "avg_loss": round(sum(x for x in profits if x <= 0) / losses, 4) if losses else None,
        "enough_for_preliminary_review": len(profits) >= 30,
    }

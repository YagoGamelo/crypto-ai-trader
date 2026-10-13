"""Leakage-aware experimental probability research; NO broker integration.

A 5-day positive price move is not a profitable executed trade. Splits and
purges are time-ordered. Calibration and evaluation use disjoint samples.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from edge_filter import evaluate_edge, wilson_lower_bound

HORIZON = 5
FEATURES = ("ret1", "ret5", "ret20", "vol20", "above20", "above50")


def _features(close):
    c = pd.Series(close, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    returns = c.pct_change()
    data = pd.DataFrame({
        "ret1": returns,
        "ret5": c.pct_change(5),
        "ret20": c.pct_change(20),
        "vol20": returns.rolling(20).std(),
        "above20": c / c.rolling(20).mean() - 1,
        "above50": c / c.rolling(50).mean() - 1,
    }, index=c.index)
    return c, data.replace([np.inf, -np.inf], np.nan)


def _classifier():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=600, random_state=42))


def _calibrator(base, X, y):
    score = base.decision_function(X).reshape(-1, 1)
    cal = LogisticRegression(max_iter=600, random_state=42)
    cal.fit(score, y)
    return cal


def _calibrated(base, calibration, X):
    return calibration.predict_proba(base.decision_function(X).reshape(-1, 1))[:, 1]


def _ece(y, p, bins=5):
    y, p = np.asarray(y), np.asarray(p)
    total = len(p)
    return float(sum((mask.sum() / total) * abs(float(y[mask].mean()) - float(p[mask].mean()))
                     for b in range(bins)
                     if (mask := ((p >= b / bins) & (p < (b + 1) / bins) if b < bins-1
                                   else ((p >= b / bins) & (p <= 1)))).any()))


def research_direction(close, horizon=HORIZON, *, round_trip_cost=.006):
    """Return diagnostic + latest calibrated UP estimate, else None.

    First fit 55%, calibrate next 20%, test final 25% with horizon-sized
    gaps on the labels. Latest forecast uses a separate final refit:
    fit older 70%, calibrate recent 30%, evaluate on no future data.
    """
    if not isinstance(horizon, int) or not 1 <= horizon <= 20:
        raise ValueError("horizon must be 1..20 completed bars")
    if isinstance(round_trip_cost,bool) or not isinstance(round_trip_cost,(int,float)) or not np.isfinite(round_trip_cost) or not 0 <= round_trip_cost <= .2:
        raise ValueError("round-trip costs must be between 0 and 20%")
    c, X = _features(close)
    if len(c) < 300 or (c <= 0).any():
        return None
    raw_forward = (c.shift(-horizon) / c) - 1
    labeled = X.iloc[:-horizon].copy()
    labeled["target"] = (raw_forward.iloc[:-horizon] > 0).astype(int)
    labeled["forward_return"] = raw_forward.iloc[:-horizon]
    labeled = labeled.replace([np.inf, -np.inf], np.nan).dropna(subset=[*FEATURES, "target", "forward_return"])
    n = len(labeled)
    if n < 250:
        return None
    train_end = int(n * .55)
    cal_end = int(n * .75)
    train = labeled.iloc[:train_end]
    calibration = labeled.iloc[train_end + horizon:cal_end]
    test = labeled.iloc[cal_end + horizon:]
    if min(len(train), len(calibration), len(test)) < 40:
        return None
    if any(segment.target.nunique() != 2 for segment in (train, calibration, test)):
        return None
    base = _classifier()
    base.fit(train[list(FEATURES)], train.target)
    calibration_model = _calibrator(base, calibration[list(FEATURES)], calibration.target)
    p = _calibrated(base, calibration_model, test[list(FEATURES)])
    y = test.target.to_numpy()
    brier = float(brier_score_loss(y, p))
    baseline_prob = float(train.target.mean())
    baseline = float(brier_score_loss(y, np.full(len(y), baseline_prob)))
    ece = _ece(y, p)
    bullish = p >= .70
    bearish = p <= .30
    bull_count = int(bullish.sum())
    bear_count = int(bearish.sum())
    bull_win = float(y[bullish].mean()) if bull_count else None
    bull_lower_bound = (wilson_lower_bound(int(y[bullish].sum()), bull_count)
                        if bull_count else None)
    # Average forward price changes per class on the held-out window.
    avg_up_return = float(test.forward_return.to_numpy()[y == 1].mean())
    avg_down_return = float(test.forward_return.to_numpy()[y == 0].mean())
    # Deduct assumed total commissions + slippage for BOTH sides.
    # This is a cost assumption, not a quote of a real broker.
    avg_net = float((test.forward_return.to_numpy()[bullish] - round_trip_cost).mean()) if bull_count else None
    bear_win = float((1 - y[bearish]).mean()) if bear_count else None
    # Conservative entry gate: accuracy of predictions above 70% must also
    # have *some* evidence on held-out data. Not proof of future accuracy.
    model_quality = bool(
        brier + .005 < baseline and ece <= .12 and
        bull_count >= 12 and bull_win is not None and bull_win >= .60 and
        bull_lower_bound is not None and bull_lower_bound > .50 and
        avg_net is not None and avg_net > 0
    )

    # Final inference refit: label overlap purged between fit/calibration.
    refit_end = int(n * .70)
    final_train = labeled.iloc[:refit_end]
    final_calibration = labeled.iloc[refit_end + horizon:]
    if min(len(final_train), len(final_calibration)) < 40 or any(
            group.target.nunique() != 2 for group in (final_train, final_calibration)):
        return None
    final = _classifier()
    final.fit(final_train[list(FEATURES)], final_train.target)
    final_cal = _calibrator(final, final_calibration[list(FEATURES)], final_calibration.target)
    current = X.iloc[[-1]][list(FEATURES)]
    if current.isna().any(axis=None):
        return None
    up = float(_calibrated(final, final_cal, current)[0])
    advantage = evaluate_edge(up, avg_up_return, avg_down_return,
                              round_trip_cost, ece)
    # Trend confirmation is descriptive, NOT a proven source of alpha.
    current_trend_above_ma50 = bool(float(current["above50"].iloc[0]) > 0)
    gate = bool(model_quality and advantage["after_cost_positive"])
    return {
        "up_pct": round(up * 100, 2),
        "down_pct": round((1 - up) * 100, 2),
        "brier": round(brier, 5),
        "baseline_brier": round(baseline, 5),
        "ece": round(ece, 5),
        "holdout_accuracy": round(float(((p >= .5) == y).mean()), 4),
        "holdout_count": len(test),
        "bullish_signals": bull_count,
        "bullish_hit_rate": round(bull_win, 4) if bull_win is not None else None,
        "bullish_wilson_lower": round(bull_lower_bound, 4) if bull_lower_bound is not None else None,
        "average_positive_return_pct": round(avg_up_return * 100, 3),
        "average_negative_return_pct": round(avg_down_return * 100, 3),
        "expected_net_pct": round(advantage["expected_net_fraction"] * 100, 3),
        "conservative_net_pct": round(advantage["conservative_net_fraction"] * 100, 3),
        "probability_haircut_pct": round(advantage["uncertainty_haircut"] * 100, 2),
        "above_ma50": current_trend_above_ma50,
        "bullish_avg_net_pct": round(avg_net * 100, 3) if avg_net is not None else None,
        "bearish_signals": bear_count,
        "bearish_hit_rate": round(bear_win, 4) if bear_win is not None else None,
        "approved_for_paper": gate,
        "passed_history_checks": model_quality,
        "better_than_baseline": bool(brier < baseline),
        "horizon": horizon,
        "assumed_round_trip_cost_pct": round(round_trip_cost*100,3),
        "method": "purged 55/20/25 train/cal/test; final 70/30 train/cal",
    }

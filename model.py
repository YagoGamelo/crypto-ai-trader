"""Chronological, leakage-aware baseline model; not financial advice."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss

FEATURES = ["ret1", "ret6", "volatility", "volume_ratio", "range"]

def prepare(df, horizon=4, round_trip_cost=0.004):
    x = df.copy()
    x["ret1"] = x.close.pct_change()
    x["ret6"] = x.close.pct_change(6)
    x["volatility"] = x["ret1"].rolling(24).std()
    x["volume_ratio"] = x.volume / x.volume.rolling(24).mean().replace(0, np.nan)
    x["range"] = (x.high - x.low) / x.close
    x["future_return"] = x.close.shift(-horizon) / x.close - 1 - round_trip_cost
    x = x.replace([np.inf, -np.inf], np.nan).iloc[:-horizon].dropna(subset=FEATURES + ["future_return"])
    x["target"] = (x.future_return > 0).astype(int)
    return x

def fit_and_score(df, horizon=4, cost=0.004):
    data = prepare(df, horizon, cost)
    if len(data) < 120:
        raise ValueError("Insufficient clean data for evaluation")
    split = int(len(data) * .7)
    # Embargo: exclude training labels overlapping the test period.
    train = data.iloc[:max(0, split - horizon)]
    test = data.iloc[split:]
    if train.target.nunique() < 2 or test.empty:
        raise ValueError("Insufficient outcome variation")
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    clf.fit(train[FEATURES], train.target)
    probabilities = clf.predict_proba(test[FEATURES])[:, 1]
    # Simple holdout diagnostic, not a guarantee of calibrated future probabilities.
    report = {
        "test_samples": len(test),
        "brier": float(brier_score_loss(test.target, probabilities)),
        "baseline_brier": float(brier_score_loss(test.target, np.repeat(train.target.mean(), len(test)))),
        "signal_count": int((probabilities >= .70).sum()),
        "signal_win_rate": float(test.target.to_numpy()[probabilities >= .70].mean()) if (probabilities >= .70).any() else None,
    }
    # Model trained only on the training period; use its last held-out forecast for demo.
    return clf, test, probabilities, report

def latest_signal(df, horizon=4, cost=0.004):
    # Refit on all fully labeled data; the last current row has no known future label.
    data = prepare(df, horizon, cost)
    if data.target.nunique() < 2:
        raise ValueError("Only one class in historical outcomes")
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    clf.fit(data[FEATURES], data.target)
    latest = df.copy()
    latest["ret1"] = latest.close.pct_change()
    latest["ret6"] = latest.close.pct_change(6)
    latest["volatility"] = latest.ret1.rolling(24).std()
    latest["volume_ratio"] = latest.volume / latest.volume.rolling(24).mean().replace(0, np.nan)
    latest["range"] = (latest.high - latest.low) / latest.close
    row = latest.iloc[[-1]][FEATURES].replace([np.inf, -np.inf], np.nan)
    if row.isna().any().any():
        raise ValueError("Latest features unavailable")
    return float(clf.predict_proba(row)[0, 1])

"""All samples synthetic: no web or broker calls."""
import numpy as np
import pandas as pd
import pytest
from research_v2 import research_direction
from top5_research import scan_all

def prices(n=650, seed=44):
    rng=np.random.default_rng(seed)
    return pd.Series(100*np.exp(np.cumsum(rng.normal(.001,.016,n))))

def test_short_history_never_forecasts():
    assert research_direction(pd.Series([100.]*30)) is None

def test_train_calibration_test_are_separate_and_bounded():
    result=research_direction(prices())
    assert result is not None
    assert 0 <= result["up_pct"] <= 100
    assert result["down_pct"] == pytest.approx(100-result["up_pct"])
    assert result["holdout_count"] >= 90
    assert 0 <= result["ece"] <= 1
    assert result["method"].startswith("purged")
    assert isinstance(result["approved_for_paper"],bool)

def test_no_incomplete_daily_candle(monkeypatch):
    import top5_research
    monkeypatch.setattr(top5_research,"WATCHLIST",[{"symbol":"TEST","category":"Ações"}])
    today=pd.Timestamp("2026-10-13")
    rng=np.random.default_rng(2)
    close=pd.Series(100*np.exp(np.cumsum(rng.normal(.001,.01,480))),
                    index=pd.bdate_range(end=today,periods=480))
    frame=pd.DataFrame({"Close":close,"High":close*1.01,"Low":close*.99})
    rows=scan_all(downloader=lambda *a,**k: frame,now=today.tz_localize("UTC"))
    assert len(rows)==1
    assert rows.iloc[0]["Data"]=="2026-10-12"
    assert rows.iloc[0]["ATR 14 %"]>0
    assert "Aprovado para virtual" in rows.columns

"""Market monitor tests are fully offline and never query exchanges."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from market_monitor import (
    build_model_rows,
    build_report,
    decision_label,
    fetch_completed_30m_quotes,
    read_json,
    run,
    update_history,
)

NOW = datetime(2026, 10, 13, 13, 29, tzinfo=timezone.utc)


def research_rows():
    return pd.DataFrame([{
        "Ativo": "AAPL", "Prob. subir (estimada)": 74.2,
        "Prob. descer (estimada)": 25.8, "Brier": .15,
        "Brier referência": .20, "Amostras teste": 145,
        "Aprovado para virtual": True, "Erro calibração %": 7.5,
        "Sinais subida >=70 teste": 12,
        "Data": "2026-10-12"
    }, {
        "Ativo": "MSFT", "Prob. subir (estimada)": 30.,
        "Prob. descer (estimada)": 70., "Brier": .14,
        "Brier referência": .17, "Amostras teste": 120,
        "Data": "2026-10-12"
    }])


def fake_quotes(now=NOW):
    return {
        "AAPL": {
            "close": 123., "change_30m_pct": 1.3,
            "close_candle_start_utc": (now-timedelta(minutes=40)).isoformat(),
            "age_minutes": 40,
            "source": "test"
        }
    }


def test_model_research_stays_separate_from_intraday_updates():
    models, asof, fresh = build_model_rows({}, NOW, scanner=research_rows)
    assert fresh is True
    assert models["AAPL"]["up_pct"] == 74.2
    assert models["MSFT"]["better_than_baseline"] is True
    previous = {"models": models, "model_updated_at": asof}
    new_models, new_asof, recomputed = build_model_rows(
        previous, NOW+timedelta(minutes=30),
        scanner=lambda: (_ for _ in ()).throw(AssertionError("Must not rescan")))
    assert recomputed is False
    assert new_asof == asof
    assert new_models == models


def test_report_has_precise_5day_horizon_and_all_170_assets():
    models, asof, _ = build_model_rows({}, NOW, scanner=research_rows)
    report = build_report({}, models, asof, fake_quotes(), NOW)
    assert report["universe_count"] == 170
    assert report["model_coverage"] == 2
    assert len(report["assets"]) == 170
    assert report["recent_30m_quotes"] == 1
    assert report["top_up"][0]["symbol"] == "AAPL"
    assert report["top_down"][0]["symbol"] == "MSFT"
    assert report["forecast_horizon"].startswith("5 velas")
    aapl = next(x for x in report["assets"] if x["symbol"] == "AAPL")
    assert aapl["signal"] == "COMPRA CANDIDATA"
    msft = next(x for x in report["assets"] if x["symbol"] == "MSFT")
    assert msft["signal"] == "VENDER SE DETIDO"


def test_cached_quote_does_not_stay_fresh():
    models, asof, _ = build_model_rows({}, NOW, scanner=research_rows)
    old = build_report({}, models, asof, fake_quotes(), NOW)
    later = build_report(old, models, asof, {}, NOW+timedelta(hours=3))
    assert later["recent_30m_quotes"] == 0
    quote = next(x for x in later["assets"] if x["symbol"] == "AAPL")["quote"]
    assert quote["age_minutes"] > 180


def test_completed_candles_only_and_missing_market_data():
    stamps=pd.date_range("2026-10-13 11:00", periods=6, freq="30min",tz="UTC")
    # 13:00 and 13:30 have not completed at 13:29.
    df=pd.DataFrame({"Close": [100,101,102,103,104,105]},index=stamps)
    def downloader(*a,**kw):
        return df
    data=fetch_completed_30m_quotes(
        NOW,assets=[{"symbol":"AAPL","category":"Ações"}],downloader=downloader)
    assert data["AAPL"]["close"] == 103
    assert data["AAPL"]["age_minutes"] == pytest.approx(59)
    assert data["AAPL"]["change_30m_pct"] == pytest.approx(round((103/102-1)*100,3))
    assert fetch_completed_30m_quotes(
        NOW,assets=[{"symbol":"AAPL","category":"Ações"}],
        downloader=lambda *a,**kw:pd.DataFrame()) == {}


def test_model_failure_reuses_previous_data_not_fabricated_data():
    models, asof, _ = build_model_rows({}, NOW, scanner=research_rows)
    previous = {"models": models, "model_updated_at": asof}
    old, when, refreshed = build_model_rows(
        previous,NOW+timedelta(hours=28),
        scanner=lambda: (_ for _ in ()).throw(RuntimeError("data provider down")))
    assert not refreshed
    assert old == models
    assert when == asof


def test_history_bounded_and_deduplicated():
    report={"generated_at_utc":NOW.isoformat(),"model_coverage":100,
            "recent_30m_quotes":20,"buy_candidates":3,"sell_if_held":2}
    recent=update_history({},report)
    recent=update_history(recent,report)
    assert len(recent["samples"]) == 1
    previous={"samples":[dict(report,time_utc=f"old{i}") for i in range(200)]}
    updated=update_history(previous,report)
    assert len(updated["samples"]) == 96


@pytest.mark.parametrize("up,down,valid,signal",[
    (70,30,True,"COMPRA CANDIDATA"),
    (69,31,True,"ESPERAR"),
    (75,25,False,"ESPERAR"),
    (50,50,True,"FECHAR SE DETIDO"),
    (29,71,True,"VENDER SE DETIDO"),
])
def test_signals_are_experimental_and_never_orders(up,down,valid,signal):
    assert decision_label(up,down,valid) == signal


def test_run_serializes_valid_json_without_network(tmp_path):
    report_path=tmp_path/"latest.json"
    history_path=tmp_path/"history.json"
    def downloader(*args,**kwargs):
        return pd.DataFrame()
    report, refreshed=run(report_path,history_path,now=NOW,
                          scanner=research_rows,downloader=downloader)
    assert refreshed
    assert report_path.exists()
    assert read_json(report_path)["model_coverage"] == 2
    assert len(read_json(history_path)["samples"]) == 1
    assert report["recent_30m_quotes"] == 0  # no fabricated prices

def test_session_gap_is_not_a_fake_30minute_move():
    stamps=pd.DatetimeIndex([
        pd.Timestamp("2026-10-12T20:00:00Z"),
        pd.Timestamp("2026-10-13T12:30:00Z"),
    ])
    candles=pd.DataFrame({"Close":[100.0,110.0]},index=stamps)
    quotes=fetch_completed_30m_quotes(NOW,assets=[{
        "symbol":"AAPL","category":"Ações"}],
        downloader=lambda *args,**kwargs:candles)
    assert quotes["AAPL"]["close"] == 110.0
    assert quotes["AAPL"]["change_30m_pct"] is None

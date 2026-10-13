"""Half-hour market report generator — data-only, no brokerage connections.

A GitHub Actions scheduled run gathers completed 30-minute candles and
periodically refreshes 5-DAILY-CANDLE model estimates. This is NOT a
30-minute forecast: separate cadences and timestamps are always disclosed.
Reports are public. No credentials, user portfolios or trading orders.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from catalog import WATCHLIST

MODEL_RECALC_HOURS = 22
MAX_HISTORY_POINTS = 96
BATCH_SIZE = 12


def utc_now():
    return datetime.now(timezone.utc)


def iso_utc(dt):
    if dt.tzinfo is None:
        raise ValueError("UTC-aware timestamp required")
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_time(raw):
    if not isinstance(raw, str) or not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
        return obj if isinstance(obj, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def build_model_rows(previous, now, *, scanner=None):
    """Reuse latest daily-model study for up to 22 hours.

    30-minute quote refreshes never masquerade as new ML forecasts.
    """
    saved = previous.get("models")
    updated = parse_time(previous.get("model_updated_at"))
    if isinstance(saved, dict) and saved and updated and timedelta(0) <= now-updated < timedelta(hours=MODEL_RECALC_HOURS):
        return saved, previous["model_updated_at"], False
    if scanner is None:
        from top5_research import scan_all
        scanner = scan_all
    try:
        frame = scanner()
    except Exception:
        if isinstance(saved, dict) and saved and updated:
            return saved, previous["model_updated_at"], False
        raise
    rows = {}
    for record in frame.to_dict("records"):
        symbol = str(record.get("Ativo") or "")
        if symbol not in {x["symbol"] for x in WATCHLIST}:
            continue
        up = _number(record.get("Prob. subir (estimada)"))
        down = _number(record.get("Prob. descer (estimada)"))
        brier = _number(record.get("Brier"))
        baseline = _number(record.get("Brier referência"))
        samples = _number(record.get("Amostras teste"))
        if (up is None or down is None or brier is None or baseline is None
                or samples is None or samples < 30
                or not 0 <= up <= 100 or not 0 <= down <= 100
                or abs(up+down-100) > 0.21):
            continue
        rows[symbol] = {
            "up_pct": round(up, 1), "down_pct": round(down, 1),
            "brier": round(brier, 4), "baseline_brier": round(baseline, 4),
            "out_of_sample_count": int(samples),
            "better_than_baseline": bool(brier < baseline),
            "daily_close_date": str(record.get("Data") or ""),
        }
    if not rows:
        if isinstance(saved, dict) and saved and updated:
            return saved, previous["model_updated_at"], False
        raise ValueError("No valid daily-model estimates. Report not published.")
    return rows, iso_utc(now), True


def fetch_completed_30m_quotes(now=None, *, assets=None, downloader=None):
    """Return freshest TWO completed 30-minute closes per available ticker.

    Uses Yahoo 30m candles, which may be absent during market closures or
    rate limiting. Never labels an in-progress candle as completed.
    """
    now = now or utc_now()
    assets = WATCHLIST if assets is None else assets
    if downloader is None:
        import yfinance as yf
        downloader = yf.download
    quotes = {}
    for start in range(0, len(assets), BATCH_SIZE):
        group = assets[start:start+BATCH_SIZE]
        names = [entry["symbol"] for entry in group]
        try:
            data = downloader(names, period="5d", interval="30m",
                              group_by="ticker", auto_adjust=True,
                              progress=False, threads=True, timeout=18)
            if data is None or data.empty:
                continue
        except Exception:
            continue
        for item in group:
            symbol = item["symbol"]
            try:
                import pandas as pd
                if isinstance(data.columns, pd.MultiIndex):
                    part = data[symbol]
                else:
                    part = data
                close = part["Close"].dropna()
                if len(close) < 2:
                    continue
                # Yahoo indexes are local-market timezone-aware for intraday.
                if close.index.tz is None:
                    continue
                completed = close.loc[close.index <= now - timedelta(minutes=30)]
                if len(completed) < 2:
                    continue
                a = _number(completed.iloc[-2])
                b = _number(completed.iloc[-1])
                if a is None or b is None or a <= 0 or b <= 0:
                    continue
                ts = completed.index[-1].to_pydatetime()
                quotes[symbol] = {
                    "close": round(b, 6),
                    "change_30m_pct": round(100*(b/a-1), 3),
                    "close_candle_start_utc": iso_utc(ts),
                    "age_minutes": round((now-ts).total_seconds()/60, 1),
                    "source": "Yahoo Finance intraday (30m, delayed possible)",
                }
            except (KeyError, ValueError, IndexError, TypeError, AttributeError):
                continue
    return quotes


def decision_label(up, down, valid):
    if up is None or down is None:
        return "SEM MODELO"
    if down >= 70:
        return "VENDER SE DETIDO"
    if up <= 50:
        return "FECHAR SE DETIDO"
    if up >= 70 and valid:
        return "COMPRA CANDIDATA"
    return "ESPERAR"


def build_report(previous, models, model_updated_at, quotes, now):
    """Do not mutate previous; all public-facing values have source metadata."""
    universe = []
    for asset in WATCHLIST:
        symbol = asset["symbol"]
        model = models.get(symbol, {}) if isinstance(models, dict) else {}
        quote = quotes.get(symbol)
        if quote is None:
            old = next((x.get("quote") for x in previous.get("assets", [])
                        if x.get("symbol") == symbol), None)
            quote = old if isinstance(old, dict) else None
        up = _number(model.get("up_pct"))
        down = _number(model.get("down_pct"))
        validated = bool(model.get("better_than_baseline"))
        universe.append({
            "symbol": symbol, "market": asset["category"],
            "prob_up_pct": up, "prob_down_pct": down,
            "better_than_baseline": validated,
            "forecast_asof_daily": model.get("daily_close_date"),
            "forecast_horizon": "5 velas diárias",
            "signal": decision_label(up, down, validated),
            "quote": quote,
        })
    available = [x for x in universe if x["prob_up_pct"] is not None]
    candidates = [x for x in available if x["better_than_baseline"]]
    top_up = sorted(candidates, key=lambda x: x["prob_up_pct"], reverse=True)[:5]
    top_down = sorted(candidates, key=lambda x: x["prob_down_pct"], reverse=True)[:5]
    recent_quotes = [x for x in universe if x["quote"] is not None and
                     (_number(x["quote"].get("age_minutes")) or 99999) <= 90]
    reported = {
        "schema_version": 1,
        "generated_at_utc": iso_utc(now),
        "model_updated_at": model_updated_at,
        "forecast_horizon": "5 velas diárias; não representa previsão a 30 minutos",
        "quote_interval": "30 minutos (última vela completa; fonte com possíveis atrasos)",
        "universe_count": len(universe),
        "model_coverage": len(available),
        "recent_30m_quotes": len(recent_quotes),
        "buy_candidates": sum(x["signal"] == "COMPRA CANDIDATA" for x in universe),
        "sell_if_held": sum(x["signal"] in ("FECHAR SE DETIDO", "VENDER SE DETIDO") for x in universe),
        "top_up": top_up, "top_down": top_down,
        "assets": universe,
        # Keep daily model studies so the next half-hour run does not refit everything.
        "models": models,
        "notes": [
            "Cotações e modelo são atualizados em cadências diferentes.",
            "Sem ordens reais ou virtuais; análise de preços apenas.",
            "Probabilidades não calibradas e podem falhar.",
            "Ações e ETFs não negociam 24/7; cripto pode ter novas velas a qualquer hora.",
            "GitHub Actions não garante execução exata de 30 em 30 minutos.",
        ],
    }
    if not available and not recent_quotes:
        raise ValueError("No current model or market quotes; preserve old report.")
    return reported


def update_history(previous_history, report):
    items = list(previous_history.get("samples", [])) if isinstance(previous_history.get("samples"), list) else []
    new_point = {
        "time_utc": report["generated_at_utc"],
        "model_coverage": report["model_coverage"],
        "recent_30m_quotes": report["recent_30m_quotes"],
        "buy_candidates": report["buy_candidates"],
        "sell_if_held": report["sell_if_held"],
    }
    if not items or items[-1].get("time_utc") != new_point["time_utc"]:
        items.append(new_point)
    return {"schema_version":1, "samples":items[-MAX_HISTORY_POINTS:]}


def run(previous_path, history_path, now=None, scanner=None, downloader=None):
    now = now or utc_now()
    previous = read_json(previous_path)
    models, model_time, recomputed = build_model_rows(previous, now, scanner=scanner)
    quotes = fetch_completed_30m_quotes(now, downloader=downloader)
    report = build_report(previous, models, model_time, quotes, now)
    history = update_history(read_json(history_path), report)
    if not isinstance(report.get("assets"), list) or not report["assets"]:
        raise ValueError("Empty market report")
    for path, payload in ((previous_path, report),(history_path,history)):
        output = Path(path)
        output.parent.mkdir(parents=True,exist_ok=True)
        temp = output.with_suffix(output.suffix+".tmp")
        temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        temp.replace(output)
    return report, recomputed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="monitor-data/data/latest.json")
    parser.add_argument("--history", default="monitor-data/data/history.json")
    args=parser.parse_args()
    report, recomputed=run(args.report,args.history)
    print(f"Market report: {report['generated_at_utc']}; model refresh={recomputed}; "
          f"coverage={report['model_coverage']}/{report['universe_count']}; "
          f"fresh quotes={report['recent_30m_quotes']}.")


if __name__ == "__main__":
    main()

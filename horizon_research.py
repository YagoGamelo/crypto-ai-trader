"""Research-only choice of direction and horizon; never places trades."""
from model import fit_and_score, latest_signal

def compare_horizons(df, horizons=(1, 2, 4, 8, 12, 24), threshold=0.70):
    """Horizons are numbers of completed candles, not fixed minutes."""
    rows = []
    for horizon in horizons:
        try:
            _, _, _, report = fit_and_score(df, horizon=horizon)
            up = latest_signal(df, horizon=horizon)
            direction = "SUBE" if up >= 0.5 else "DESCE"
            confidence = max(up, 1 - up)
            # This baseline was trained for profitable long trades, not a
            # symmetric binary up/down contract. Its complement is NOT a
            # validated probability of winning a DOWN contract.
            rows.append({
                "Velas": horizon,
                "Direção indicativa": direction,
                "Confiança não calibrada": round(confidence, 4),
                "Brier": round(report["brier"], 4),
                "Referência Brier": round(report["baseline_brier"], 4),
                "Amostras": report["test_samples"],
                "Aprovado para operar": False,
            })
        except (ValueError, KeyError, IndexError):
            continue
    rows.sort(key=lambda r: (r["Brier"] - r["Referência Brier"], -r["Amostras"]))
    return rows

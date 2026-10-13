"""Read-only, deterministic risk/return scorecard.

Not a recommendation, chance of success, parameter optimizer or validation
of a 400%-a-year claim. A backtest is just an experiment using past data.
"""
from __future__ import annotations

import math


def audit_backtest(result):
    """Check whether single-asset walk-forward *deserves further study*.

    The gates are deliberately strict and predeclared. A pass is NOT approval
    for live trading, and multiple testing over different tickers still adds
    selection bias.
    """
    required = ("return_pct", "max_drawdown_pct", "bars_tested",
                "completed_trades", "total_fees_usd")
    if not isinstance(result, dict) or not all(key in result for key in required):
        raise ValueError("Backtest results incomplete")
    values = {key: float(result[key]) for key in required}
    if (not all(math.isfinite(x) for x in values.values())
            or values["bars_tested"] < 0 or values["completed_trades"] < 0
            or values["total_fees_usd"] < 0 or values["max_drawdown_pct"] > 0):
        raise ValueError("Backtest results invalid")
    reasons = []
    if values["bars_tested"] < 252:
        reasons.append("Menos de 252 sessões fora da amostra")
    if values["completed_trades"] < 30:
        reasons.append("Menos de 30 operações encerradas")
    if values["return_pct"] <= 0:
        reasons.append("Rentabilidade líquida histórica não positiva")
    if values["max_drawdown_pct"] < -15:
        reasons.append("Queda histórica superior a 15%")
    if not reasons:
        reasons.append("Os filtros mínimos passaram, mas NÃO demonstram retorno futuro")
    passed = (values["bars_tested"] >= 252
              and values["completed_trades"] >= 30
              and values["return_pct"] > 0
              and values["max_drawdown_pct"] >= -15)
    return {
        "result": "CANDIDATO A NOVOS TESTES" if passed else "SEM VALIDAÇÃO SUFICIENTE",
        "further_research_candidate": passed,
        "reasons": reasons,
        "goal_400_annual_verified": False,
        "live_trading_allowed": False,
        "risk_notice": "Dados passados, um único ativo e seleção múltipla não permitem inferir probabilidade de +400% anual.",
    }

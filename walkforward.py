"""Per-symbol walk-forward DEMONSTRATION, not evidence of profitability.

Model at t uses completed closes strictly before t. Fills simulated at the
NEXT market open, with spread/slippage and per-side fees. Single-asset spot
(long only), conservative budget and loss management. No optimization of
thresholds on the test period; user-defined 70/50 policy is fixed.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from research_v2 import research_direction
from risk_rules import entry_stop_fraction, budget_for_entry, trailing_exit

FEE = .002
SLIPPAGE = .001
INITIAL_USD = 50.
RESERVE_SHARE = .30
BUY_THRESHOLD = .70
SELL_THRESHOLD = .50


def _drawdown(values):
    vals = np.asarray(values, dtype=float)
    if len(vals) == 0:
        return 0.
    return float(np.min(vals / np.maximum.accumulate(vals) - 1) * 100)


def backtest_one_asset(frame, *, initial_usd=INITIAL_USD, horizon=5,
                       retrain_every=5, start_bars=320):
    """Simulate a complete out-of-sample phase on 2-5 years of OHLC.

    Price source must be a single asset in its account currency; USD assumed
    by user-facing panels only for US-listed tickers. History not split-adjusted
    and dividends are ignored; use auto_adjusted OHLC from data provider.
    """
    required={"Open", "Close"}
    if not isinstance(frame,pd.DataFrame) or not required.issubset(frame.columns):
        raise ValueError("Requires Open and Close price columns")
    data=frame[["Open", "Close"]].astype(float).replace([np.inf,-np.inf],np.nan).dropna()
    if len(data)<start_bars+30:
        raise ValueError("At least 350 completed bars required")
    if not isinstance(retrain_every,int) or retrain_every<1:
        raise ValueError("Invalid retrain interval")
    if not math.isfinite(initial_usd) or initial_usd<=0:
        raise ValueError("Invalid starting balance")
    data=data.loc[(data.Open>0)&(data.Close>0)]
    if len(data)<start_bars+30:
        raise ValueError("Too many invalid prices")
    cash=float(initial_usd)
    reserved=0.
    units=0.
    cost=0.
    entry_price=peak=0.
    fees_total=0.
    wins=losses=0
    last_signal=None
    history=[]
    trades=[]
    invested_days=0
    for i in range(start_bars,len(data)):
        # Candles through yesterday only. Today is never in training/features.
        if last_signal is None or (i-start_bars)%retrain_every==0:
            last_signal=research_direction(data.Close.iloc[:i],horizon=horizon)
        model=last_signal
        close_before=float(data.Close.iloc[i-1])
        opening=float(data.Open.iloc[i])
        action=None
        if units>0:
            peak=max(peak,close_before)
            exit_by_price=(close_before<=entry_price*(1-entry_stop_fraction(None))
                           or trailing_exit(entry_price,peak,close_before))
            exit_by_prob=(model is not None and model["up_pct"]<=SELL_THRESHOLD*100)
            if exit_by_price or exit_by_prob:
                fill=opening*(1-SLIPPAGE)
                gross=units*fill
                fee=gross*FEE
                realized=gross-fee-cost
                reserve=max(0,realized)*RESERVE_SHARE
                cash+=gross-fee-reserve
                reserved+=reserve
                fees_total+=fee
                wins+=int(realized>0)
                losses+=int(realized<=0)
                trades.append({"date":str(data.index[i]),"action":"SELL","price":round(fill,4),
                               "p_up":model["up_pct"] if model else None,
                               "net_pnl":round(realized,4),"reserved":round(reserve,4),
                               "reason":"price protection" if exit_by_price else "up <=50%"})
                units=entry_price=peak=cost=0.
                action="SELL"
        # No same-bar reversal from SELL to BUY.
        if (units==0 and action is None and model and model["approved_for_paper"]
                and model["up_pct"]>=BUY_THRESHOLD*100):
            investible=cash
            budget=budget_for_entry(cash,investible,None)
            if budget>0:
                fill=opening*(1+SLIPPAGE)
                units=budget/(fill*(1+FEE))
                fee=fill*units*FEE
                cash-=budget
                cost=budget
                entry_price=peak=fill
                fees_total+=fee
                trades.append({"date":str(data.index[i]),"action":"BUY","price":round(fill,4),
                               "p_up":model["up_pct"],"net_pnl":0.,"reserved":0.,
                               "reason":"up >=70%, validated"})
        invested_days+=int(units>0)
        equity=cash+reserved+units*float(data.Close.iloc[i])
        history.append({"date":str(data.index[i]),"equity":round(equity,6),
                        "cash":round(cash,6),"reserved":round(reserved,6),
                        "p_up":model["up_pct"] if model else None})
    equity_final=history[-1]["equity"]
    benchmark_entry=float(data.Open.iloc[start_bars])*(1+SLIPPAGE)
    benchmark_final=float(data.Close.iloc[-1])*(1-SLIPPAGE)
    benchmark=100*(benchmark_final*(1-FEE)/(benchmark_entry*(1+FEE))-1)
    days=len(history)
    total_pct=100*(equity_final/initial_usd-1)
    annualized=100*((equity_final/initial_usd)**(252/days)-1) if days>=126 and equity_final>0 else None
    return {
        "initial_usd":initial_usd,"equity_usd":round(equity_final,4),
        "return_pct":round(total_pct,2),
        "annualized_pct":round(annualized,2) if annualized is not None else None,
        "max_drawdown_pct":round(_drawdown([initial_usd]+[h["equity"] for h in history]),2),
        "benchmark_buy_hold_pct":round(benchmark,2),
        "invested_days_pct":round(100*invested_days/days,1),
        "winning_sells":wins,"losing_sells":losses,
        "completed_trades":wins+losses,
        "total_fees_usd":round(fees_total,4),
        "reserved_usd":round(reserved,4),
        "bars_tested":days,
        "trades":trades,
        "equity_curve":history,
        "notes":"Simulated next open, 0.2% fee/side and 0.1% slippage/side; long only; no dividends, taxes, FX or live quotes."
    }

"""Risk policies for virtual research only (not brokerage stop orders)."""
from __future__ import annotations
import math

MAX_POSITION_FRACTION = .20
MAX_RISK_FRACTION = .01
DEFAULT_STOP = .05
MAX_STOP = .08
MIN_STOP = .03
MIN_TRADE = 2.


def entry_stop_fraction(atr_pct=None):
    """Volatility-responsive stop at 2 ATR, between 3 and 8 percent.

    ATR missing -> 5% fallback. Daily close only; market gaps can exceed it.
    """
    if atr_pct is None:
        return DEFAULT_STOP
    try:
        atr = float(atr_pct)
    except (TypeError, ValueError):
        return DEFAULT_STOP
    if not math.isfinite(atr) or atr <= 0:
        return DEFAULT_STOP
    return min(MAX_STOP, max(MIN_STOP, 2 * atr / 100))


def budget_for_entry(cash, investible_equity, atr_pct=None):
    """Cap allocation to 20% equity AND intended initial stop risk to 1%.

    Returns budget INCLUDING virtual entry fee. Exposure not a loss guarantee.
    """
    cash, investible_equity = float(cash), float(investible_equity)
    if not all(math.isfinite(x) and x >= 0 for x in (cash, investible_equity)):
        raise ValueError("Invalid account balance")
    stop = entry_stop_fraction(atr_pct)
    amount = min(cash, investible_equity * MAX_POSITION_FRACTION,
                 (investible_equity * MAX_RISK_FRACTION) / stop)
    return round(amount, 6) if amount >= MIN_TRADE else 0.


def trailing_exit(entry, peak, price, atr_pct=None):
    """Arm a trailing exit after +4% or 1.5 ATR; then trail 3% or 1 ATR.

    Uses observed COMPLETED closes only, so cannot sell at the exact peak.
    """
    if not all(math.isfinite(float(v)) and float(v)>0 for v in (entry,peak,price)):
        raise ValueError("Invalid prices")
    try:
        atr = float(atr_pct) / 100
    except (TypeError, ValueError):
        atr = 0
    if not math.isfinite(atr) or atr<=0:
        atr=0
    arm=max(.04,1.5*atr)
    trail=max(.03,atr)
    return peak >= entry*(1+arm) and price <= peak*(1-trail)

"""Educational LONG Call / LONG Put payoff at CONTRACT EXPIRATION.

Not a live option chain or execution engine. No naked option selling,
binary payoffs, derivatives API or brokerage connection.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


def _positive(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label}: valor inválido")
    try:
        n=float(value)
    except (ValueError, TypeError) as err:
        raise ValueError(f"{label}: valor inválido") from err
    if not math.isfinite(n) or n <= 0:
        raise ValueError(f"{label}: deve ser positivo e finito")
    return n


@dataclass(frozen=True)
class LongOption:
    kind: str
    strike: float
    premium_per_unit: float
    multiplier: int = 100
    contracts: int = 1
    commission_total: float = 0.0

    def __post_init__(self):
        if self.kind not in ("CALL", "PUT"):
            raise ValueError("Só são simuladas compras Call e Put")
        _positive(self.strike, "Strike")
        _positive(self.premium_per_unit, "Prémio")
        if (type(self.multiplier) is not int or type(self.contracts) is not int
                or not 1 <= self.multiplier <= 100000 or not 1 <= self.contracts <= 100):
            raise ValueError("Multiplicador ou número de contratos inválido")
        if (isinstance(self.commission_total, bool) or
                not isinstance(self.commission_total,(int,float)) or
                not math.isfinite(self.commission_total) or self.commission_total < 0):
            raise ValueError("Comissões inválidas")

    @property
    def units(self):
        return self.multiplier * self.contracts

    @property
    def debit(self):
        return self.premium_per_unit * self.units + self.commission_total

    @property
    def max_loss(self):
        return -self.debit

    @property
    def breakeven(self):
        per_unit_fee = self.commission_total / self.units
        if self.kind == "CALL":
            return self.strike + self.premium_per_unit + per_unit_fee
        return self.strike - self.premium_per_unit - per_unit_fee

    @property
    def max_gain(self):
        if self.kind == "CALL":
            return None  # theoretical infinity, not guaranteed profit
        return self.strike * self.units - self.debit

    def payout(self, underlying_expiry):
        """Net P/L, excluding FX and any exercise/assignment charges."""
        price=float(underlying_expiry)
        if not math.isfinite(price) or price < 0:
            raise ValueError("Preço final inválido")
        intrinsic = (max(0.0, price-self.strike) if self.kind=="CALL"
                     else max(0.0, self.strike-price))
        return intrinsic * self.units - self.debit

    def chart(self, *, current_price=None, points=121):
        """Prices and P/L to draw a payoff chart, NOT a price forecast."""
        import numpy as np
        current = self.strike if current_price is None else _positive(current_price,"Preço atual")
        if not isinstance(points,int) or points < 20 or points > 1000:
            raise ValueError("Número de pontos inválido")
        left=max(.0,min(current,self.strike)*.55)
        right=max(current,self.strike,self.breakeven if self.breakeven>0 else 0)*1.50
        if right<=left:
            right=self.strike*2
        prices=np.linspace(left,right,points)
        return prices.tolist(),[self.payout(p) for p in prices]

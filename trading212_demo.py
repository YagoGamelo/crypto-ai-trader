"""Trading 212 *demo-only* client. Hard-coded host; never accesses live trading.

Official API: https://docs.trading212.com/api
Authentication: HTTP Basic with API Key / API Secret, not a single API token.
No credentials are stored, displayed, logged, or committed to source control.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

DEMO_BASE = "https://demo.trading212.com/api/v0"
# Deliberately no configuration for the live host.
ALLOWED_PATHS = frozenset({
    "/equity/account/summary",
    "/equity/positions",
    "/equity/orders",
    "/equity/metadata/instruments",
    "/equity/orders/limit",
})
TICKER_RE = re.compile(r"^[A-Z0-9._-]{1,40}$")
MAX_DEMO_ORDER_EUR = 10.0


class Trading212DemoError(Exception):
    """Sanitized error: never displays tokens or broker response bodies."""


@dataclass(frozen=True)
class Credentials:
    key: str
    secret: str

    def __post_init__(self):
        if not isinstance(self.key, str) or not self.key.strip():
            raise Trading212DemoError("A API Key da conta DEMO não foi configurada.")
        if not isinstance(self.secret, str) or not self.secret.strip():
            raise Trading212DemoError("A API Secret da conta DEMO não foi configurada.")


class DemoClient:
    def __init__(self, credentials: Credentials, session=None):
        self.credentials = credentials
        self.session = session if session is not None else requests.Session()

    def _request(self, method: str, path: str, payload=None) -> Any:
        method = method.upper()
        if path not in ALLOWED_PATHS:
            raise Trading212DemoError("Endpoint não autorizado pelo conector demo.")
        if method not in ("GET", "POST"):
            raise Trading212DemoError("Método HTTP não autorizado.")
        if method == "POST" and path != "/equity/orders/limit":
            raise Trading212DemoError("Só são permitidas ordens limite DEMO.")
        url = DEMO_BASE + path
        try:
            response = self.session.request(
                method,
                url,
                auth=HTTPBasicAuth(self.credentials.key, self.credentials.secret),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json=payload if method == "POST" else None,
                timeout=(5, 15),
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise Trading212DemoError("Não foi possível contactar a Trading 212 demo.") from None
        status = response.status_code
        if status in (301, 302, 303, 307, 308):
            raise Trading212DemoError("O servidor devolveu um redirecionamento inesperado.")
        if status in (401, 403):
            raise Trading212DemoError("Credenciais demo inválidas ou sem permissões suficientes.")
        if status == 429:
            raise Trading212DemoError("Limite de pedidos atingido. Experimenta mais tarde.")
        if status < 200 or status >= 300:
            raise Trading212DemoError(f"Pedido demo recusado (HTTP {status}).")
        try:
            return response.json()
        except ValueError:
            raise Trading212DemoError("Resposta inválida da API demo.") from None

    def account_summary(self) -> dict:
        data = self._request("GET", "/equity/account/summary")
        if not isinstance(data, dict):
            raise Trading212DemoError("Formato inesperado dos dados de conta.")
        return data

    def positions(self) -> list:
        data = self._request("GET", "/equity/positions")
        if not isinstance(data, list):
            raise Trading212DemoError("Formato inesperado das posições.")
        return data

    def pending_orders(self) -> list:
        data = self._request("GET", "/equity/orders")
        if not isinstance(data, list):
            raise Trading212DemoError("Formato inesperado das ordens pendentes.")
        return data

    def instruments(self) -> list:
        # Rate limit is strict (once / 50 seconds); call only on explicit request.
        data = self._request("GET", "/equity/metadata/instruments")
        if not isinstance(data, list):
            raise Trading212DemoError("Formato inesperado dos instrumentos.")
        return data

    def place_demo_limit(
        self, *, instrument: dict, quantity: float, limit_price: float,
        account_currency: str, available_to_trade: float,
        quantity_available_to_sell: float = 0,
        max_order_value: float = MAX_DEMO_ORDER_EUR,
        explicitly_confirmed: bool = False,
    ) -> dict:
        """Send one intentional LIMIT order to *demo*, never live.

        Amount is capped in account currency. The prototype restricts
        instruments to matching currency and requires a verified ticker from
        the broker's instruments endpoint. This is purposely stricter than
        Trading 212's API: FX-converted orders are not supported here.
        """
        if not explicitly_confirmed:
            raise Trading212DemoError("A ordem precisa de confirmação explícita.")
        if not isinstance(instrument, dict):
            raise Trading212DemoError("Seleciona um instrumento válido da Trading 212.")
        ticker = instrument.get("ticker")
        currency = instrument.get("currencyCode")
        if not isinstance(ticker, str) or not TICKER_RE.fullmatch(ticker):
            raise Trading212DemoError("Ticker de instrumento inválido.")
        if currency != account_currency or not isinstance(currency, str):
            raise Trading212DemoError("A moeda do instrumento deve coincidir com a moeda da conta demo.")
        for val in (quantity, limit_price, available_to_trade, quantity_available_to_sell, max_order_value):
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
                raise Trading212DemoError("Quantidade, preço ou saldo inválidos.")
        if quantity == 0 or limit_price <= 0 or available_to_trade < 0 or quantity_available_to_sell < 0:
            raise Trading212DemoError("Quantidade, preço ou saldo inválidos.")
        if max_order_value <= 0 or max_order_value > MAX_DEMO_ORDER_EUR:
            raise Trading212DemoError("Limite máximo de ordem demo inválido.")
        value = abs(quantity * limit_price)
        if value > max_order_value + 1e-9:
            raise Trading212DemoError(f"Esta ordem ultrapassa o limite demo de {max_order_value:.2f} {currency}.")
        if quantity > 0 and value > available_to_trade:
            raise Trading212DemoError("Saldo demo disponível insuficiente.")
        if quantity < 0 and abs(quantity) > quantity_available_to_sell + 1e-9:
            raise Trading212DemoError("Não é possível vender mais ações do que as disponíveis.")
        # The API is NOT idempotent. Never automatically retry POST requests.
        data = self._request("POST", "/equity/orders/limit", payload={
            "ticker": ticker,
            "quantity": round(quantity, 8),
            "limitPrice": round(limit_price, 6),
            "timeValidity": "DAY",
        })
        if not isinstance(data, dict):
            raise Trading212DemoError("Formato inesperado da resposta à ordem.")
        return data

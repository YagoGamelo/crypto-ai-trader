"""Offline unit tests: never send requests to Trading 212."""
import pytest
import requests

from trading212_demo import Credentials, DemoClient, Trading212DemoError, DEMO_BASE


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self.payload = {} if payload is None else payload

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses=None, fail=False):
        self.calls = []
        self.responses = list(responses or [FakeResponse()])
        self.fail = fail

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.fail:
            raise requests.Timeout("Sensitive data should not appear in logs")
        return self.responses.pop(0)


def client(fake):
    return DemoClient(Credentials("demo-key", "demo-secret"), session=fake)


def test_read_account_uses_demo_and_basic_auth():
    fake = FakeSession([FakeResponse(payload={"currency": "EUR", "cash": {"availableToTrade": 50}})])
    result = client(fake).account_summary()
    assert result["currency"] == "EUR"
    method, url, kwargs = fake.calls[0]
    assert method == "GET"
    assert url == DEMO_BASE + "/equity/account/summary"
    assert "live.trading212.com" not in url
    assert kwargs["auth"].username == "demo-key"
    assert kwargs["auth"].password == "demo-secret"
    assert kwargs["allow_redirects"] is False
    assert kwargs["timeout"] == (5, 15)


def test_other_reads():
    fake = FakeSession([FakeResponse(payload=[]), FakeResponse(payload=[]),
                        FakeResponse(payload=[{"ticker": "AAPL_US_EQ"}])])
    c = client(fake)
    assert c.positions() == []
    assert c.pending_orders() == []
    assert c.instruments()[0]["ticker"] == "AAPL_US_EQ"


def test_demo_limit_order_with_explicit_confirmation():
    fake = FakeSession([FakeResponse(payload={"id": 123, "status": "NEW"})])
    result = client(fake).place_demo_limit(
        instrument={"ticker": "TEST_EU_EQ", "currencyCode": "EUR"},
        quantity=0.5, limit_price=10, account_currency="EUR",
        available_to_trade=50, explicitly_confirmed=True,
    )
    assert result["id"] == 123
    method, url, kwargs = fake.calls[0]
    assert method == "POST"
    assert url == DEMO_BASE + "/equity/orders/limit"
    assert kwargs["json"] == {"ticker": "TEST_EU_EQ", "quantity": 0.5,
                                "limitPrice": 10, "timeValidity": "DAY"}


@pytest.mark.parametrize("invalid", [
    {"quantity": 1.1, "limit_price": 10},
    {"quantity": -1, "limit_price": 5, "quantity_available_to_sell": 0},
    {"quantity": 0.1, "limit_price": 0},
    {"quantity": 0.1, "limit_price": float("nan")},
    {"quantity": 0.1, "limit_price": 10, "account_currency": "USD"},
    {"quantity": 0.1, "limit_price": 10, "explicitly_confirmed": False},
])
def test_rejects_invalid_orders_without_network(invalid):
    fake = FakeSession()
    kwargs = {"instrument": {"ticker": "TEST_EU_EQ", "currencyCode": "EUR"},
              "quantity": 0.1, "limit_price": 10, "account_currency": "EUR",
              "available_to_trade": 50, "explicitly_confirmed": True}
    kwargs.update(invalid)
    with pytest.raises(Trading212DemoError):
        client(fake).place_demo_limit(**kwargs)
    assert fake.calls == []


def test_sell_must_be_held():
    fake = FakeSession([FakeResponse(payload={"id": 2})])
    result = client(fake).place_demo_limit(
        instrument={"ticker": "TEST_EU_EQ", "currencyCode": "EUR"},
        quantity=-0.5, limit_price=10, account_currency="EUR",
        available_to_trade=0, quantity_available_to_sell=0.5,
        explicitly_confirmed=True,
    )
    assert result["id"] == 2


@pytest.mark.parametrize("status", [401, 403, 408, 429, 500, 302])
def test_http_errors_are_sanitized(status):
    fake = FakeSession([FakeResponse(status=status)])
    with pytest.raises(Trading212DemoError) as caught:
        client(fake).account_summary()
    assert "demo-secret" not in str(caught.value)
    assert "demo-key" not in str(caught.value)


def test_network_failure_is_sanitized():
    fake = FakeSession(fail=True)
    with pytest.raises(Trading212DemoError) as caught:
        client(fake).account_summary()
    assert "Sensitive data" not in str(caught.value)


def test_no_credentials():
    with pytest.raises(Trading212DemoError):
        Credentials("key", "")

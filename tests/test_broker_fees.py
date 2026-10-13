import pytest
from brokers import PROVIDERS, preview_roundtrip_eur, comparable_stock_costs

def test_all_brokers_have_official_links_and_api_status():
    assert len(PROVIDERS)>=6
    assert len({p["name"] for p in PROVIDERS})==len(PROVIDERS)
    for provider in PROVIDERS:
        assert all(provider[key].startswith("https://") for key in ["website","fees","api_docs","regulator"])
        assert isinstance(provider["api_ok"], bool)

def test_roundtrip_foreign_currency_stock_examples():
    names=dict(comparable_stock_costs(50))
    assert names["Trading 212 Invest"]==pytest.approx(.15)
    assert names["XTB"]==pytest.approx(.50)
    assert names["DEGIRO"]==pytest.approx(4.25)
    assert "Interactive Brokers" not in names
    eur=dict(comparable_stock_costs(50,"EUR"))
    assert eur["Trading 212 Invest"]==pytest.approx(0.0)
    assert eur["XTB"]==pytest.approx(0.0)
    assert eur["DEGIRO"]==pytest.approx(4.0)

def test_crypto_not_compared_as_stock():
    for broker in PROVIDERS:
        if broker["type"]=="Criptomoedas":
            assert preview_roundtrip_eur(broker,50) is None

def test_invalid_inputs():
    with pytest.raises(ValueError):
        comparable_stock_costs(0)

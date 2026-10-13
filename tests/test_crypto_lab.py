"""Fully offline crypto/meme Kraken market tests; no private API calls."""
from datetime import datetime, timezone, timedelta

import pytest

from crypto_lab import study_crypto, expected_cost_fraction, allowed_symbol
from crypto_paper import new_wallet, equity, decision

NOW=datetime(2026,10,13,12,0,tzinfo=timezone.utc)


class FakeKraken:
    def __init__(self, pair="BTC/USD", close=100.0, volume=3000.0,
                 bid=99.9, ask=100.1, latest_minutes_ago=30, spot=True):
        self.pair=pair
        self.close=close
        self.volume=volume
        self.bid=bid
        self.ask=ask
        self.latest_minutes_ago=latest_minutes_ago
        self.markets={pair:{"spot":spot,"active":True}}

    def load_markets(self):
        return self.markets

    def fetch_ohlcv(self,symbol,timeframe,limit):
        assert symbol==self.pair and timeframe=="30m"
        last_start=NOW-timedelta(minutes=self.latest_minutes_ago)
        rows=[]
        for i in range(510):
            t=last_start-timedelta(minutes=30*(509-i))
            px=self.close*(1+.0003*(i-509))
            rows.append([int(t.timestamp()*1000),px,px*1.01,px*.99,px,self.volume])
        return rows

    def fetch_ticker(self,pair):
        return {"bid":self.bid,"ask":self.ask}


def fake_model(close,horizon,round_trip_cost):
    assert horizon==4
    assert len(close)>=330
    assert round_trip_cost>0
    return {"up_pct":75.0,"down_pct":25.0,"approved_for_paper":True,
            "holdout_count":110,"ece":.04,"bullish_signals":15}


def test_crypto_public_spot_study_and_meme_costs(monkeypatch):
    monkeypatch.setattr("crypto_lab.research_direction",fake_model)
    result=study_crypto("BTC",now=NOW,exchange=FakeKraken())
    assert result["paper_buy_eligible"]
    assert result["forecast_horizon_minutes"]==120
    assert result["is_meme"] is False
    assert result["quote_volume_24h_usd"]>100000
    assert result["spread_pct"]==pytest.approx(.2,abs=.02)
    assert result["estimated_round_trip_cost_pct"]==pytest.approx(1.4)
    assert expected_cost_fraction(True)>expected_cost_fraction(False)


def test_meme_requires_liquidity_and_market_listing(monkeypatch):
    monkeypatch.setattr("crypto_lab.research_direction",fake_model)
    market=FakeKraken(pair="PEPE/USD",close=.001,volume=40000000,
                      bid=.00099,ask=.00101)
    study=study_crypto("PEPE",now=NOW,exchange=market)
    assert study["is_meme"]
    assert study["estimated_round_trip_cost_pct"]==pytest.approx(2.8)
    assert study["spread_pct"]>1.5
    assert not study["paper_buy_eligible"]
    assert "Spread elevado" in study["risk_notes"]
    with pytest.raises(ValueError):
        study_crypto("FAKECOIN",now=NOW,exchange=market)
    with pytest.raises(ValueError):
        study_crypto("SHIB",now=NOW,exchange=market)


def test_spot_only_and_stale_candles_fail_closed(monkeypatch):
    monkeypatch.setattr("crypto_lab.research_direction",fake_model)
    with pytest.raises(ValueError):
        study_crypto("BTC",now=NOW,exchange=FakeKraken(spot=False))
    study=study_crypto("BTC",now=NOW,exchange=FakeKraken(latest_minutes_ago=240))
    assert not study["paper_buy_eligible"]
    assert "Preço desatualizado" in study["risk_notes"]


def create_study(base="BTC",up=75,eligible=True,price=100,at="2026-10-13T12:00:00+00:00"):
    return {"pair":f"{base}/USD","base":base,"is_meme":base=="PEPE",
            "timeframe":"30m","last_closed_utc":at,"data_age_minutes":0,
            "price_usd":price,"slippage_per_side_pct":1.0 if base=="PEPE" else .3,
            "paper_buy_eligible":eligible,
            "model":{"up_pct":up,"down_pct":100-up,"approved_for_paper":eligible}}


def test_crypto_wallet_buy_sell_and_reserve():
    wallet=new_wallet()
    info=create_study()
    assert decision(wallet,info).startswith("COMPRAR")
    assert wallet["position"] is None
    assert decision(wallet,info,execute=True).startswith("COMPRA VIRTUAL")
    assert wallet["position"]
    assert wallet["cash"]==pytest.approx(40)
    assert "já foi avaliada" in decision(wallet,info,execute=True)
    later=create_study(up=50,price=115,at="2026-10-13T12:30:00+00:00")
    assert decision(wallet,later,execute=True).startswith("VENDA VIRTUAL")
    assert wallet["position"] is None
    assert wallet["reserved"]>0
    assert equity(wallet)>50


def test_memecoin_allocation_half_and_no_short():
    wallet=new_wallet()
    assert decision(wallet,create_study(base="PEPE",up=20),execute=True).startswith("ESPERAR")
    assert wallet["position"] is None
    # A fresh candle is required; same-candle entries cannot be retried.
    assert decision(wallet,create_study(base="PEPE",up=80),execute=True).startswith("ESPERAR")
    assert decision(wallet,create_study(base="PEPE",up=80,
                    at="2026-10-13T12:30:00+00:00"),execute=True).startswith("COMPRA")
    assert wallet["cash"]==pytest.approx(45)
    other=create_study(base="BTC",up=92,at="2026-10-13T12:30:00+00:00")
    assert decision(wallet,other,execute=True).startswith("MANTER")
    assert wallet["position"]["pair"]=="PEPE/USD"


def test_insufficient_validation_blocks_buy():
    wallet=new_wallet()
    assert decision(wallet,create_study(up=98,eligible=False),execute=True).startswith("ESPERAR")
    assert not wallet["trades"]

def test_exchange_minimum_larger_than_wallet_blocks_virtual_entry(monkeypatch):
    monkeypatch.setattr("crypto_lab.research_direction",fake_model)
    fake=FakeKraken()
    fake.markets["BTC/USD"]["limits"]={"cost":{"min":25},"amount":{"min":0}}
    result=study_crypto("BTC",now=NOW,exchange=fake)
    assert not result["paper_buy_eligible"]
    assert not result["minimum_order_ok"]
    assert "Mínimo de ordem superior ao orçamento virtual" in result["risk_notes"]


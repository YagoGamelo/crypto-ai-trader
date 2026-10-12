from paper import connect, snapshot, step

def test_buy_and_stop(tmp_path):
    db = connect(str(tmp_path / "test.db"))
    assert snapshot(db, 100)["equity"] == 50
    assert step(db, 100, .8, enabled=True).startswith("BUY")
    s = snapshot(db, 100)
    assert 0 < s["units"] < 0.1
    assert step(db, 95, .8, enabled=True).startswith("SELL")
    assert snapshot(db, 95)["units"] == 0

def test_no_trade_without_permission(tmp_path):
    db = connect(str(tmp_path / "test.db"))
    assert step(db, 100, .99, enabled=False) == "Pausado"
    assert snapshot(db, 100)["cash"] == 50

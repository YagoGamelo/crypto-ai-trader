"""Isolated paper-trading ledger. No live broker endpoints or credentials."""
import math
import sqlite3
from datetime import datetime, timezone

INITIAL_BALANCE_USD = 50.0
FEE_RATE = 0.002
MAX_ALLOCATION = 0.20
STOP_LOSS = 0.03
TAKE_PROFIT = 0.06
PROFIT_RESERVE = 0.30

def connect(path=":memory:"):
    # An in-memory database is private to the returned connection. The app
    # stores one connection per Streamlit browser session, never in a global cache.
    db = sqlite3.connect(path, check_same_thread=False)
    db.execute("""CREATE TABLE IF NOT EXISTS wallet (
        id INTEGER PRIMARY KEY CHECK(id=1), cash REAL NOT NULL, units REAL NOT NULL,
        entry REAL NOT NULL, reserved REAL NOT NULL DEFAULT 0)""")
    db.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, action TEXT,
        price REAL, units REAL, fee REAL, reason TEXT)""")
    columns = {row[1] for row in db.execute("PRAGMA table_info(wallet)")}
    if "reserved" not in columns:  # migration for legacy local DBs
        db.execute("ALTER TABLE wallet ADD COLUMN reserved REAL NOT NULL DEFAULT 0")
    db.execute("INSERT OR IGNORE INTO wallet (id,cash,units,entry,reserved) VALUES (1, ?, 0, 0, 0)",
               (INITIAL_BALANCE_USD,))
    db.commit()
    return db

def _valid_price(price):
    if not math.isfinite(price) or price <= 0:
        raise ValueError("O preço tem de ser positivo e finito")

def snapshot(db, price):
    _valid_price(price)
    cash, units, entry, reserved = db.execute(
        "SELECT cash,units,entry,reserved FROM wallet WHERE id=1").fetchone()
    return {"cash": cash, "units": units, "entry": entry, "reserved": reserved,
            "equity": cash + units * price + reserved}

def step(db, price, probability, threshold=0.70, enabled=True):
    if not enabled:
        return "Pausado"
    _valid_price(price)
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Probabilidade inválida")
    if not 0 < threshold <= 1:
        raise ValueError("Limiar inválido")
    s = snapshot(db, price)
    reason = ""
    action = None
    qty = fee = 0.0
    if s["units"] > 0:
        if price <= s["entry"] * (1 - STOP_LOSS):
            reason = "stop loss virtual"
        elif price >= s["entry"] * (1 + TAKE_PROFIT):
            reason = "take profit virtual"
        elif probability < 0.45:
            reason = "sinal fraco"
        if reason:
            action = "SELL"
            qty = s["units"]
            fee = qty * price * FEE_RATE
            proceeds = qty * price - fee
            paid = qty * s["entry"] * (1 + FEE_RATE)
            realized_net = proceeds - paid
            reserve = min(proceeds, max(0.0, realized_net) * PROFIT_RESERVE)
            db.execute(
                "UPDATE wallet SET cash=?,units=0,entry=0,reserved=? WHERE id=1",
                (s["cash"] + proceeds - reserve, s["reserved"] + reserve))
            reason += f"; lucro líquido {realized_net:.4f} USD; reserva {reserve:.4f} USD"
    elif probability >= threshold:
        budget = min(s["cash"], s["equity"] * MAX_ALLOCATION)
        if budget >= 2:
            action = "BUY"
            qty = budget / (price * (1 + FEE_RATE))
            fee = qty * price * FEE_RATE
            reason = "limiar de probabilidade (não calibrada)"
            db.execute(
                "UPDATE wallet SET cash=?,units=?,entry=? WHERE id=1",
                (max(0.0, s["cash"] - qty * price - fee), qty, price))
    if action:
        db.execute(
            "INSERT INTO trades (ts,action,price,units,fee,reason) VALUES (?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), action, price, qty, fee, reason))
        db.commit()
        return f"{action}: {reason}"
    return "WAIT: sem trade válido"

def history(db):
    return db.execute(
        "SELECT ts,action,price,units,fee,reason FROM trades ORDER BY id DESC LIMIT 100"
    ).fetchall()

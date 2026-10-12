"""Local paper-only portfolio. No API keys or live order endpoints."""
import sqlite3
from datetime import datetime, timezone

INITIAL_EUR = 50.0
FEE_RATE = .002
MAX_ALLOCATION = .20
STOP_LOSS = .03
TAKE_PROFIT = .06

def connect(path="paper.db"):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS wallet (id INTEGER PRIMARY KEY CHECK(id=1), cash REAL NOT NULL, units REAL NOT NULL, entry REAL NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, action TEXT, price REAL, units REAL, fee REAL, reason TEXT)")
    db.execute("INSERT OR IGNORE INTO wallet VALUES (1, ?, 0, 0)", (INITIAL_EUR,))
    db.commit()
    return db

def snapshot(db, price):
    cash, units, entry = db.execute("SELECT cash, units, entry FROM wallet WHERE id=1").fetchone()
    return {"cash": cash, "units": units, "entry": entry, "equity": cash + units * price}

def step(db, price, probability, threshold=.70, enabled=True):
    if not enabled:
        return "Pausado"
    if price <= 0:
        raise ValueError("Invalid price")
    s = snapshot(db, price)
    action = None
    reason = ""
    qty = fee = 0.0
    if s["units"] > 0:
        if price <= s["entry"] * (1 - STOP_LOSS):
            reason = "stop loss (simulated)"
        elif price >= s["entry"] * (1 + TAKE_PROFIT):
            reason = "take profit (simulated)"
        elif probability < .45:
            reason = "weak signal"
        if reason:
            action = "SELL"
            qty = s["units"]
            fee = qty * price * FEE_RATE
            db.execute("UPDATE wallet SET cash=?, units=0, entry=0 WHERE id=1", (s["cash"] + qty * price - fee,))
    elif probability >= threshold:
        budget = min(s["cash"], s["equity"] * MAX_ALLOCATION)
        if budget >= 2:
            action = "BUY"
            qty = budget / (price * (1 + FEE_RATE))
            fee = qty * price * FEE_RATE
            reason = "probability threshold"
            db.execute("UPDATE wallet SET cash=?, units=?, entry=? WHERE id=1", (s["cash"] - qty * price - fee, qty, price))
    if action:
        db.execute("INSERT INTO trades (ts, action, price, units, fee, reason) VALUES (?, ?, ?, ?, ?, ?)", (datetime.now(timezone.utc).isoformat(), action, price, qty, fee, reason))
        db.commit()
        return f"{action}: {reason}"
    return "WAIT: no valid trade"

def history(db):
    return db.execute("SELECT ts, action, price, units, fee, reason FROM trades ORDER BY id DESC LIMIT 100").fetchall()

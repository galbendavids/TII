"""
This file thinks about the prices and gives a simple suggestion (a signal).

What it does (in simple words):
- Reads price history from the database.
- Calculates a 30-day average and how far today's price is from that average (z-score).
- Chooses an action: buy USD, sell USD, or hold, with a confidence number.
- Saves that decision in the database and returns it.

What it contains:
- One function compute_signal() that does all the steps above.

Why it matters / impact:
- Turns raw numbers into a simple idea of what to do next.
- The API and any user can fetch this to understand the current situation quickly.
"""

import pandas as pd
from sqlalchemy import text
from db import engine, IS_SQLITE

def compute_signal():
    """Compute and store a simple z-score based trading signal.

    Kid-friendly idea: We compare today's price to the last 30 days.
    If it's much higher than usual, we say "USD is expensive"; if lower, "USD is cheap".
    If it's normal, we suggest to wait (hold).
    """
    q = """
      SELECT ts, close FROM fx_rates
      WHERE pair='USDILS'
      ORDER BY ts
    """
    # SQLite stores ts as TEXT; parse on read. Postgres uses timestamptz; pandas can parse too.
    df = pd.read_sql(q, engine)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    if len(df) < 40:
        return None

    df["ma30"] = df["close"].rolling(30).mean()
    df["sd30"] = df["close"].rolling(30).std()
    df["z30"] = (df["close"] - df["ma30"]) / df["sd30"]
    last = df.dropna().iloc[-1]
    z = float(last["z30"])

    if z >= 1.5:
        action, conf = "usd_to_ils", min((z-1.5)/2.0+0.6, 0.95)
        rationale = f"z30={z:.2f} מעל 1.5 ⇒ דולר יקר יחסית"
    elif z <= -1.5:
        action, conf = "ils_to_usd", min((-1.5-z)/2.0+0.6, 0.95)
        rationale = f"z30={z:.2f} מתחת -1.5 ⇒ דולר זול יחסית"
    else:
        action, conf = "hold", 0.5
        rationale = f"z30={z:.2f} בתחום ניטרלי"

    ts = pd.to_datetime(last["ts"], utc=True)
    with engine.begin() as conn:
        if IS_SQLITE:
            conn.execute(text("""
              INSERT INTO fx_signals (ts,pair,action,confidence,rationale)
              VALUES (:ts,'USDILS',:action,:confidence,:rationale)
              ON CONFLICT(ts) DO UPDATE SET
                action=excluded.action, confidence=excluded.confidence, rationale=excluded.rationale
            """), {"ts": ts.isoformat(), "action": action, "confidence": conf, "rationale": rationale})
        else:
            conn.execute(text("""
              INSERT INTO fx_signals (ts,pair,action,confidence,rationale)
              VALUES (:ts,'USDILS',:action,:confidence,:rationale)
              ON CONFLICT (ts) DO UPDATE SET
                action=EXCLUDED.action, confidence=EXCLUDED.confidence, rationale=EXCLUDED.rationale
            """), {"ts": ts, "action": action, "confidence": conf, "rationale": rationale})

    # Extra details for emails/UI (current state and simple future expectations)
    latest_close = float(last["close"]) if "close" in last else float(df.iloc[-1]["close"])  # safety
    ma30 = float(last["ma30"])
    sd30 = float(last["sd30"])
    upper_band = ma30 + 1.5 * sd30
    lower_band = ma30 - 1.5 * sd30
    projected_mean = ma30  # naive expectation: mean reversion toward 30d average

    return {
        "ts": ts,
        "pair": "USDILS",
        "action": action,
        "confidence": conf,
        "rationale": rationale,
        "latest_close": latest_close,
        "ma30": ma30,
        "sd30": sd30,
        "z30": z,
        "projected_mean": projected_mean,
        "upper_band": upper_band,
        "lower_band": lower_band,
    }
"""
This file is the data fetcher and saver.

What it does (in simple words):
- Downloads USD/ILS prices from the internet (using yfinance) like grabbing data from a weather site.
- Saves or updates that price data inside our database so we can use it later.

What it contains:
- Settings for which currency pair to fetch (PAIR) and the exact online symbol (TICKER).
- A function upsert_rates() that puts rows into the fx_rates table, updating if they already exist.
- Two helpers: run_full_backfill() for all history, run_daily_update() for recent days.

Why it matters / impact:
- Without fresh price data, the API and the signals have nothing to work with.
- This keeps the database current so decisions are based on up-to-date info.
"""

import os, pandas as pd, yfinance as yf
from sqlalchemy import text
from db import engine, init_db, IS_SQLITE

PAIR = os.getenv("PAIR", "USDILS")
TICKER = "USDILS=X"  # yfinance symbol

def upsert_rates(df: pd.DataFrame):
    """Insert or update price rows into fx_rates.

    Kid-friendly idea: If we already have a page for a day, we rewrite it with the newest info.
    Otherwise, we add a new page.
    """
    df = df.reset_index().rename(columns={
        "Date":"ts","Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"
    })
    df["pair"] = PAIR
    rows = df[["ts","pair","close","high","low","open","volume"]].to_dict(orient="records")
    if IS_SQLITE:
        # SQLite upsert uses INSERT ... ON CONFLICT DO UPDATE with different syntax
        sql = text("""
            INSERT INTO fx_rates (ts,pair,close,high,low,open,volume)
            VALUES (:ts,:pair,:close,:high,:low,:open,:volume)
            ON CONFLICT(ts) DO UPDATE SET
              close=excluded.close, high=excluded.high, low=excluded.low,
              open=excluded.open, volume=excluded.volume, pair=excluded.pair
        """)
    else:
        sql = text("""
            INSERT INTO fx_rates (ts,pair,close,high,low,open,volume)
            VALUES (:ts,:pair,:close,:high,:low,:open,:volume)
            ON CONFLICT (ts) DO UPDATE SET
              close=EXCLUDED.close, high=EXCLUDED.high, low=EXCLUDED.low,
              open=EXCLUDED.open, volume=EXCLUDED.volume, pair=EXCLUDED.pair
        """)
    with engine.begin() as conn:
        conn.execute(sql, rows)

def run_full_backfill():
    """Load all available historical data and save it.

    Useful when we start for the first time and need the whole history.
    """
    init_db()
    hist = yf.download(TICKER, period="max", interval="1d", auto_adjust=False, progress=False)
    if not hist.empty:
        upsert_rates(hist)

def run_daily_update():
    """Load just the recent days and save them.

    Useful for daily or scheduled runs so we stay up to date.
    """
    init_db()
    hist = yf.download(TICKER, period="7d", interval="1d", auto_adjust=False, progress=False)
    if not hist.empty:
        upsert_rates(hist)

if __name__ == "__main__":
    # ברירת מחדל ל-run: עדכון קצר
    run_daily_update()
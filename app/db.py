"""
This file is like the house plan for our data.

What it does (in simple words):
- Connects to a database using a secret address called DATABASE_URL.
- Creates two tables if they don't exist yet:
  1) fx_rates: keeps daily price information for USD to ILS (like a history diary).
  2) fx_signals: keeps simple trading suggestions the app computes.

What it contains:
- A database engine (the door we use to talk to the database).
- Text instructions (DDL) that describe how to build the tables.
- A function named init_db() that builds the tables safely.

Why it matters / impact:
- Without this, the rest of the app would have nowhere to store or read data.
- Other files call init_db() to make sure the database is ready before working.
"""

from sqlalchemy import create_engine, text
import os

# If DATABASE_URL is missing, fall back to a local SQLite file in /data.
# This enables "RunPod-only" deployments without any external database.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/app.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite:")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Dialect-specific table definitions so it works on both Postgres and SQLite
if IS_SQLITE:
    DDL = """
    CREATE TABLE IF NOT EXISTS fx_rates (
      ts TEXT PRIMARY KEY,
      pair TEXT NOT NULL,
      close REAL NOT NULL,
      high  REAL,
      low   REAL,
      open  REAL,
      volume REAL
    );
    CREATE TABLE IF NOT EXISTS fx_signals (
      ts TEXT PRIMARY KEY,
      pair TEXT NOT NULL,
      action TEXT NOT NULL,
      confidence REAL NOT NULL,
      rationale TEXT
    );
    """
else:
    DDL = """
    CREATE TABLE IF NOT EXISTS fx_rates (
      ts timestamptz PRIMARY KEY,
      pair text NOT NULL,
      close numeric NOT NULL,
      high  numeric,
      low   numeric,
      open  numeric,
      volume numeric
    );
    CREATE TABLE IF NOT EXISTS fx_signals (
      ts timestamptz PRIMARY KEY,
      pair text NOT NULL,
      action text NOT NULL,
      confidence numeric NOT NULL,
      rationale text
    );
    """

def init_db():
    """Create the tables if they don't exist yet.

    How it works (kid-friendly):
    - Think of the database like a library.
    - If shelves (tables) are missing, we build them.
    - We split the DDL text into separate commands and run each one.
    - Using engine.begin() makes sure everything is neat and safe.
    """
    with engine.begin() as conn:
        for stmt in DDL.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
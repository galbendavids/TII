"""
This file is the web front door (API) for the app.

What it does (in simple words):
- Starts a FastAPI server so other programs (or people) can ask for data.
- Offers buttons (endpoints) to get the latest price, load new data, run signals, and read the latest signal.

What it contains:
- A FastAPI app called `app`.
- Startup step that prepares the database.
- Four endpoints:
  1) GET /rates/latest -> returns the newest USDILS price.
  2) POST /ingest -> fetches recent data and saves it.
  3) POST /signals/run -> calculates a simple trading signal and stores it.
  4) GET /signals/latest -> returns the newest stored signal.

Why it matters / impact:
- This is how the outside world talks to our system.
- The cron job and any dashboards can call these endpoints to keep data fresh and get decisions.
"""

from fastapi import FastAPI
from sqlalchemy import text
from db import engine, init_db
from ingestor import run_daily_update
from signals import compute_signal
from emailer import send_email

app = FastAPI(title="USDILS FX API")

@app.on_event("startup")
def _startup():
    """Prepare the database at application start."""
    init_db()

@app.get("/rates/latest")
def latest_rate():
    """Return the most recent close price for USDILS, or empty if missing."""
    q = text("SELECT ts, close FROM fx_rates WHERE pair='USDILS' ORDER BY ts DESC LIMIT 1")
    with engine.begin() as conn:
        row = conn.execute(q).mappings().first()
    return row or {}

@app.post("/ingest")
def ingest():
    """Fetch recent prices and save them to the database."""
    run_daily_update()
    return {"status":"ok"}

@app.post("/signals/run")
def run_signals():
    """Compute the latest signal and store it, returning the result."""
    out = compute_signal()
    return out or {"status":"not_enough_data"}

@app.get("/signals/latest")
def latest_signal():
    """Return the most recent stored signal for USDILS, or empty if missing."""
    q = text("SELECT * FROM fx_signals WHERE pair='USDILS' ORDER BY ts DESC LIMIT 1")
    with engine.begin() as conn:
        row = conn.execute(q).mappings().first()
    return row or {}

@app.post("/signals/notify")
def run_and_notify():
    """Compute the latest signal, store it, and email the suggestion/details."""
    result = compute_signal()
    if not result:
        return {"status": "not_enough_data"}

    subject = f"USDILS Signal: {result['action']} (conf {result['confidence']:.2f})"
    body = (
        "USDILS Daily Signal\n"
        f"Time: {result['ts']}\n"
        f"Action: {result['action']}\n"
        f"Confidence: {result['confidence']:.2f}\n"
        f"Reason: {result['rationale']}\n\n"
        "Current State\n"
        f"Latest Close: {result['latest_close']:.4f}\n"
        f"MA30: {result['ma30']:.4f}\n"
        f"SD30: {result['sd30']:.4f}\n"
        f"Z30: {result['z30']:.2f}\n\n"
        "Future Estimation (simple)\n"
        f"Projected Mean (reversion): {result['projected_mean']:.4f}\n"
        f"Upper Band (z=+1.5): {result['upper_band']:.4f}\n"
        f"Lower Band (z=-1.5): {result['lower_band']:.4f}\n"
    )
    try:
        send_email(subject, body)
        status = "emailed"
    except Exception as e:
        status = f"email_failed: {e}"
    return {"status": status, **result}

@app.get("/dashboard")
def dashboard():
    """Simple HTML dashboard to see latest metrics and trigger checks."""
    # Use latest stored signal if exists; if not, compute one (may return None)
    latest = latest_signal()
    html = f"""
    <html>
      <head>
        <title>USDILS Dashboard</title>
        <meta name=viewport content="width=device-width, initial-scale=1" />
        <style>
          body {{ font-family: sans-serif; max-width: 800px; margin: 20px auto; padding: 0 12px; }}
          .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 12px 0; }}
          button {{ padding: 10px 14px; border-radius: 6px; border: 1px solid #888; cursor: pointer; }}
          code {{ background: #f6f6f6; padding: 2px 4px; border-radius: 4px; }}
        </style>
      </head>
      <body>
        <h1>USDILS Dashboard</h1>
        <div class="card">
          <h2>Latest Stored Signal</h2>
          <pre>{latest}</pre>
        </div>
        <div class="card">
          <h2>Actions</h2>
          <button onclick="trigger('/signals/run')">Compute Signal (no email)</button>
          <button onclick="trigger('/signals/notify')">Compute + Send Email</button>
          <button onclick="trigger('/ingest')">Ingest Latest Prices</button>
          <p id="out"></p>
        </div>
        <script>
          async function trigger(path) {{
            const res = await fetch(path, {{ method: 'POST' }});
            const txt = await res.text();
            document.getElementById('out').innerText = txt;
            setTimeout(() => location.reload(), 1000);
          }}
        </script>
      </body>
    </html>
    """
    return html
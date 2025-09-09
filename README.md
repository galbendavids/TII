## WhatIfWealth — Backtesting Portfolio App (Streamlit)

An interactive Streamlit app to analyze a custom stock portfolio against popular benchmarks over different historical periods. You can:
- Compare cumulative returns, volatility, Sharpe ratio, and max drawdown vs. a benchmark.
- Visualize performance and drawdowns with Plotly charts.
- Generate optimized alternative allocations under constraints (locking tickers, safety level, limited change budget).
- Export a concise PDF report with portfolio composition and key metrics.

The UI is primarily in Hebrew and is designed for ease of use.

### Project structure
- `app.py` — Streamlit application (UI, analytics, optimization, PDF export)
- `dockerfile` — Container build file. Note: the current file in this repo is tailored for a different (FastAPI + cron) setup. For this Streamlit app, use the Docker instructions below which include a minimal Dockerfile you can copy-paste.

### Requirements
- Python 3.10+ (tested with 3.11)
- macOS, Linux, or Windows
- Internet connectivity (for `yfinance` data)

Python packages used:
- `streamlit`, `pandas`, `yfinance`, `plotly`, `numpy`, `reportlab`

---

## Run locally (recommended for development)

### 1) Clone
```bash
git clone <your-repo-url>
cd TII
```

### 2) Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -V
```

### 3) Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Run the app
```bash
streamlit run app.py
```

By default Streamlit starts at `http://localhost:8501`.

### 5) Using the app
- הגדר טווח תאריכים בסרגל הצד.
- הזן מניות ואחוזי השקעה (סה"כ 100%).
- בחר Benchmark להשוואה (SPY/QQQ/...).
- לחץ "הרץ ניתוח" לראות מדדים, גרפים והשוואות.
- לאופטימיזציה, לחץ "הצע שילוב חדש", קבע רמת ביטחון ונעילת מניות.
- ניתן להוריד דוח PDF מסכם.

### Troubleshooting (local)
- If data is missing: try different dates or tickers; free data can be sparse or rate limited.
- If Streamlit doesn’t open: ensure the terminal shows a URL and that port 8501 is not blocked.
- If `reportlab` fails to render fonts: update `reportlab` or try reinstalling it.

---

## Run in Docker (locally)

The provided `dockerfile` in this repo is for a different app stack. Replace its contents with the following minimal Dockerfile content for Streamlit (or create a new file named exactly `dockerfile` with this content):

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py /app/

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
```

### Build and run
```bash
docker build -t whatifwealth:latest -f dockerfile .
docker run --rm -p 8501:8501 whatifwealth:latest
```

Open `http://localhost:8501`.

Notes:
- If you prefer to reuse the existing `dockerfile`, you must adapt it to Streamlit (expose port 8501 and run Streamlit instead of Uvicorn). The snippet above already does this.

---

## Deploy on RunPod

RunPod can host containerized apps. For Streamlit, you’ll run a CPU pod serving port 8501.

### 1) Prepare and push an image
Use the single Dockerfile provided in this repo (`dockerfile`).
```bash
docker login
docker build -t <dockerhub-user>/whatifwealth:latest -f dockerfile .
docker push <dockerhub-user>/whatifwealth:latest
```

### 2) Create a Pod on RunPod (recommended)
1. In RunPod, click "Create Pod".
2. Select a CPU template (GPU not required).
3. Container Image: `docker.io/<dockerhub-user>/whatifwealth:latest`.
4. Container Port: add TCP `8501`.
5. Command/Entrypoint: leave default if you used the Dockerfile above (it already starts Streamlit on 0.0.0.0:8501).
6. Volumes: not required for this app.
7. Environment variables: none required.
8. Start the Pod.

### 3) Access the app
- Once running, open the Pod details and locate the public URL for port 8501.
- Navigate to `http://<YOUR-POD-HOST>:8501`.

### 4) Alternative: Serverless HTTP (optional)
RunPod Serverless can work, but Streamlit apps often expect a long-lived process and websocket support. A full (persistent) Pod is recommended for reliability.

### Troubleshooting (RunPod)
- If the page doesn’t load: confirm port 8501 is exposed and public routing is enabled.
- If the container exits: check Pod logs. Ensure the entrypoint runs Streamlit, not Uvicorn.
- Data errors from `yfinance`: transient rate limits or unavailable symbols; try again or change tickers/date range.

---

## Frequently asked questions

- Which Python version should I use?
  - Python 3.10 or 3.11 is recommended.

- Do I need any API keys?
  - No. `yfinance` pulls public data without keys.

- Can I change the UI language?
  - The code is straightforward Streamlit; modify the text in `app.py` as needed.

- Can I export CSVs instead of PDF?
  - Not built-in. You can add a `st.download_button` with a generated CSV similar to the PDF block.

---

## Development tips
- Use a virtual environment to isolate dependencies.
- Streamlit’s `st.cache_data` is used for basic caching. If changing logic dramatically, clear cache with the "Rerun" menu in the app.
- The optimization routine samples many portfolios; on large universes or long windows, increase resources or reduce iterations for speed.


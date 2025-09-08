## USDILS FX App — Run end-to-end on RunPod (Step-by-step for a programmer)

This guide takes you from 0 to 100: you’ll deploy a tiny API that:
- Downloads USD/ILS prices daily
- Stores them in Postgres
- Computes a simple buy/sell/hold signal
- Serves everything over HTTP

We’ll run it all in a Docker container on RunPod. No prior cloud experience needed.

### 1) What you need (quick checklist)
- A free Docker Hub account (or any container registry)
- A RunPod account
- Your computer with Docker installed

### 2) Database? Not needed — using SQLite on RunPod
By default, the app writes to a SQLite file at `/data/app.db` inside the container.
No external DB is required. If you still want Postgres, set `DATABASE_URL`.

### 3) Clone the project locally
```bash
git clone <your fork or this repo>
cd TII
```

Project layout (important bits):
- `app/main.py`: FastAPI app and endpoints
- `app/ingestor.py`: downloads USDILS prices and saves to DB
- `app/signals.py`: computes the trading signal and saves to DB
- `app/db.py`: creates tables and connects to DB
- `app/supercronic.cron`: schedules daily ingest + signal run inside the container
- `dockerfile`: builds the container that runs both cron and the API

### 4) Build your Docker image
Pick a unique image name, like `dockerhub-username/usdils-mvp:latest`.

```bash
docker login
docker build -t dockerhub-username/usdils-mvp:latest .
docker push dockerhub-username/usdils-mvp:latest
```

If the push works, your image is now in Docker Hub.

### 5) Prepare environment variables
The app needs:
- `PAIR` (optional): defaults to `USDILS`
- Email/SMTP (optional, for notifications):
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
  - `EMAIL_FROM`, `EMAIL_TO` (comma-separated allowed)

Example values:
```
PAIR=USDILS
SMTP_HOST=smtp.yourprovider.com
SMTP_PORT=587
SMTP_USER=your_user
SMTP_PASS=your_password
EMAIL_FROM=alerts@yourdomain.com
EMAIL_TO=you@yourdomain.com
```

### 6) Create a RunPod deployment (SQLite only)
RunPod can run your container 24/7. You have two main options:

- Serverless (HTTP): Good for on-demand calls; may sleep between requests.
- Persistent Pod (recommended here): Always on; perfect for cron + API.

Steps (Persistent Pod):
1. In RunPod, click “Create Pod”.
2. Choose a CPU-only template (GPU not required) or create a Custom Image.
3. Set “Container Image” to your Docker image, e.g. `docker.io/dockerhub-username/usdils-mvp:latest`.
4. Set “Container Ports” to expose TCP 8000.
5. Add Environment Variables:
   - `PAIR` = `USDILS` (optional)
   - SMTP vars if you want email alerts
6. Add a Persistent Volume in RunPod (e.g., mount `/data`) so your SQLite file survives restarts.
7. Start the Pod.

Our dockerfile launches two things:
- Supercronic (reads `app/supercronic.cron`) to run daily jobs
- Uvicorn FastAPI server on port 8000

### 7) Open the API
Once the Pod is running:
1. Find your Pod’s public URL/port mapping in RunPod.
2. Test the live docs:
   - Open: `http://<YOUR-POD-HOST>:8000/docs`
   - You should see the FastAPI Swagger UI.

### 8) Manually trigger a first data load and signal
Use the API buttons in `/docs` or curl from your laptop:
```bash
curl -X POST http://<YOUR-POD-HOST>:8000/ingest
curl -X POST http://<YOUR-POD-HOST>:8000/signals/run
```

Then check results:
```bash
curl http://<YOUR-POD-HOST>:8000/rates/latest
curl http://<YOUR-POD-HOST>:8000/signals/latest
```

If you see JSON with values, the pipeline works.

Signal response now includes extra fields for the dashboard and emails:
```
{
  ts, pair, action, confidence, rationale,
  latest_close, ma30, sd30, z30,
  projected_mean, upper_band, lower_band
}
```

### 9) Daily automation (cron)
Inside the container, supercronic runs these every day:
- 14:05 → POST `/ingest`
- 14:07 → POST `/signals/notify`

You can change times by editing `app/supercronic.cron` and rebuilding/pushing the image.

### 10) Troubleshooting tips
- API not reachable: confirm RunPod port 8000 is exposed and publicly routed.
- DB issues: verify `DATABASE_URL` is correct and accessible from the internet.
- Empty data: wait a minute and try `/ingest` again; yfinance rate limits sometimes.
- Logs: open the Pod logs in RunPod; look for Python tracebacks.

### 11) Optional: Customize the pair
Set `PAIR` env var (e.g., `EURILS`) and change the `TICKER` in `app/ingestor.py`
from `"USDILS=X"` to the matching yfinance symbol (e.g., `"EURILS=X"`), then rebuild
and push the image.

### 12) Endpoints quick reference
- `GET /rates/latest` → newest price (ts, close)
- `POST /ingest` → fetch recent prices and store
- `POST /signals/run` → compute/store latest signal
- `GET /signals/latest` → newest stored signal
- `POST /signals/notify` → compute signal and send email (uses SMTP env vars)
- `GET /dashboard` → simple HTML page to view metrics and trigger a check

That’s it — you’re live on RunPod with a tiny data+signals API!



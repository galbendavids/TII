# This file tells Docker how to build a tiny computer (container) for our app.
# What it does (simple):
# - Starts from Python 3.11.
# - Installs a tiny scheduler called supercronic to run timed tasks.
# - Copies our code in and installs Python dependencies.
# - Opens the web port (8000) and starts both the scheduler and the API.
# Why it matters:
# - Makes the app easy to run anywhere in the same, repeatable way.
FROM python:3.11-slim

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# supercronic (קרון-לייט לדוקר)
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.31/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic
RUN curl -fsSLo /usr/local/bin/${SUPERCRONIC} ${SUPERCRONIC_URL} \
    && chmod +x /usr/local/bin/${SUPERCRONIC}

WORKDIR /app
COPY app/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app
COPY app/supercronic.cron /etc/supercronic.cron

EXPOSE 8000
# מריץ גם את ה-API וגם את הקרון
VOLUME ["/data"]
CMD sh -c "/usr/local/bin/supercronic -quiet /etc/supercronic.cron & \
           uvicorn main:app --host 0.0.0.0 --port 8000"
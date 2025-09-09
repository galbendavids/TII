# Minimal Dockerfile for Streamlit app
FROM python:3.11-slim

WORKDIR /app

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY app.py /app/

EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
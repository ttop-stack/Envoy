FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy alert engine script
COPY alert_engine.py .

# Run the alert engine
CMD ["python", "-u", "alert_engine.py"]

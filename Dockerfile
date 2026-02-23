FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends 
    gcc 
    libffi-dev 
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY templates/ ./templates/
COPY config/ ./config/
COPY data/ ./data/

# Start server
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8080"]

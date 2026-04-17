FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl libmagic1 postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r raze && useradd -r -g raze -d /app -s /sbin/nologin raze

# Install Python dependencies as root (before switching user)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set ownership
RUN chown -R raze:raze /app

USER raze

# Migrations run via entrypoint; uvicorn starts the API
# In production, run migrations as a separate init step before scaling replicas.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips='*'"]

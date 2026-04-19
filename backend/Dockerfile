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

# Copy database initialization script
COPY --chown=raze:raze db-init.sh /app/db-init.sh
RUN chmod +x /app/db-init.sh

# Database tables and schema are managed via Alembic migrations
# db-init.sh runs migrations, then uvicorn starts the API
CMD ["/bin/sh", "-c", "/app/db-init.sh && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips=*"]

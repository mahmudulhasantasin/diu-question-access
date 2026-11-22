# Production Dockerfile for DIU Question MCP & REST Server
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt .

# Install dependencies into wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final minimal production stage
FROM python:3.12-slim

WORKDIR /app

# Install curl for container health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source code
COPY . .

# Create persistent data directory and set permissions
RUN mkdir -p /app/data && \
    useradd -m -u 1001 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DIU_DATA_DIR=/app/data \
    DIU_DB_PATH=/app/data/diu_questions.db \
    DIU_SERVER_HOST=0.0.0.0 \
    DIU_SERVER_PORT=8000

# Expose HTTP / MCP port
EXPOSE 8000

# Mountable volume for PDF files and SQLite DB
VOLUME ["/app/data"]

# Healthcheck for container orchestrators (Render, Railway, AWS ECS, GCP Cloud Run)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: Runs the production FastAPI & MCP SSE server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

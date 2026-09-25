# ==============================================================================
# Stage 1: Build & Dependency Wheel Compilation
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir --user -r requirements.txt

# ==============================================================================
# Stage 2: Minimal Production Runtime
# ==============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install curl for container health check probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Strict Least Privilege: Create non-root system user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy installed python dependencies from builder with proper non-root ownership
COPY --chown=appuser:appgroup --from=builder /root/.local /home/appuser/.local

# Copy application backend, frontend static assets, and configurations
COPY --chown=appuser:appgroup backend /app/backend
COPY --chown=appuser:appgroup frontend /app/frontend

# Ensure storage directories exist with non-root ownership
RUN mkdir -p /app/storage /tmp/irecruit_uploads && \
    chown -R appuser:appgroup /app/storage /tmp/irecruit_uploads

# Set PATH for user-installed Python binaries
ENV PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

# Switch to non-root execution
USER appuser

EXPOSE 8000

# Periodic health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Launch ASGI application server
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

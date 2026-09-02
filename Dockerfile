# Stage 1: Builder
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies required for compiling Python packages (e.g., asyncpg C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/ --upgrade pip && \
    pip install --no-cache-dir --extra-index-url https://us-central1-python.pkg.dev/riccardo-blog-test-v1/python-pypi/simple/ -r requirements.txt


# Stage 2: Production Runtime
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install runtime PostgreSQL client library required for database connectivity
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and group for runtime execution
RUN groupadd -r conductor-group && \
    useradd -r -g conductor-group -s /sbin/nologin -d /app conductor-runtime

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application source code and set proper ownership
COPY --chown=conductor-runtime:conductor-group . /app

# Switch to non-root user
USER conductor-runtime

# Expose HTTP service port
EXPOSE 8080

# Execute FastAPI via Uvicorn with 2 workers tailored for Cloud Run concurrency
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]

# Use Python 3.14 slim image
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    librdkafka-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the official installer (faster than pip)
# Note: We use uv for all package management instead of pip
# Install to system-wide location so it's available to all users
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    chmod +x /usr/local/bin/uv
ENV PATH="/usr/local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using uv
# Note: Using uv pip install for compatibility with existing Python environments
RUN uv pip install --system -e .

# Copy application code
COPY app/ ./app/
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Note: CMD is not set here - it's defined in docker-compose.yml for environment-specific control
# In production, use gunicorn with uvicorn workers: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

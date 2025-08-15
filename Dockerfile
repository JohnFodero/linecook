# Use the official astral uv image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Install build dependencies and runtime dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    cups-client \
    cups-bsd \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv, then remove build dependencies to save space
RUN uv sync --frozen --no-dev && \
    apt-get purge -y cmake build-essential && \
    apt-get autoremove -y && \
    apt-get clean

# Copy application code and modules
COPY main.py config.py ./
COPY api/ ./api/
COPY services/ ./services/
COPY static/ ./static/

# Create directories for input/output and temp files (optional, can be mounted)
RUN mkdir -p test_inputs test_outputs tmp

# Expose port 8000
EXPOSE 8000

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the FastAPI server using uv
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

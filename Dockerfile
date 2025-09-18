# Use Python 3.11 slim base image for optimal size and performance
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# Install system dependencies for audio processing and PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libsndfile1 \
    ffmpeg \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create directory for database migrations (if using Alembic)
RUN mkdir -p ./alembic

# Expose the port FastAPI runs on
EXPOSE 8000

# Health check to ensure container is running properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI application with production settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
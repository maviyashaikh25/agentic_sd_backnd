FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for PostgreSQL client / compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker build cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000 (FastAPI default in local run)
EXPOSE 8000

# Run Uvicorn backend server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Small, standard Python image
FROM python:3.11-slim

# Prevents Python from writing .pyc files and buffers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build tools only if needed by dependencies (safe default)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
&& rm -rf /var/lib/apt/lists/*

# Copy only dependency/install metadata first (better build cache)
COPY setup.py README.md /app/

# Copy packages
COPY aims /app/aims
COPY pyhypercycle_aim /app/pyhypercycle_aim

# Install your project (pulls dependencies declared in setup.py)
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

# Expose FastAPI port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "aims.api:app", "--host", "0.0.0.0", "--port", "8000"]

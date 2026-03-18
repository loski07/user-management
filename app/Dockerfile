# --- Stage 1: Builder ---
FROM python:3.13-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml src/main.py ./

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir --target=/app/site-packages .

# --- Stage 2: Runtime (Distroless) ---
FROM gcr.io/distroless/python3-debian13:nonroot

LABEL maintainer="loski07@gmail.com"
LABEL description="FastAPI service for managing users with S3 and DynamoDB"

WORKDIR /app

COPY --from=builder /app/site-packages /app/site-packages
COPY --from=builder /app/main.py /app/main.py

ENV PYTHONPATH=/app/site-packages
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

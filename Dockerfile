# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
# Build frontend to dist
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

# Stage 2: Python Backend & Unified Server
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (build-essential/gcc if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt pydantic-settings faiss-cpu sentence-transformers "fastapi>=0.100.0"

COPY . .
# Copy compiled static frontend into place
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

ENV PORT=8000
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
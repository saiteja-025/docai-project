# ============================================================
# Stage 1: Build Frontend (React + Vite + TailwindCSS v4)
# ============================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./

# Bake the API base URL so the SPA talks to /api/v1 on the same origin.
# No CORS needed in production — backend serves both frontend and API.
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

# ============================================================
# Stage 2: Python Backend + Unified Server
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Build tools required by some ML packages (e.g. faiss-cpu, tokenizers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cleaner Python output in logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ============================================================
# C3 Fix: Pre-cache the HuggingFace embedding model during
# the Docker BUILD so it is baked into the image layer.
# Without this, the model (~90 MB) would download on every
# cold start, risking a Render startup timeout.
# ============================================================
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
print('Pre-caching all-MiniLM-L6-v2 embedding model...'); \
SentenceTransformer('all-MiniLM-L6-v2'); \
print('Model cached successfully.')"

# Copy application source
COPY . .

# Copy compiled frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

ENV PORT=8000

CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}

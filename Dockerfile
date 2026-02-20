## Multi-stage Dockerfile
# Stage 1: build frontend (Vite)
FROM node:18-alpine AS build-frontend
WORKDIR /app/stock-front

# Install dependencies (package.json only is copied first for cache)
COPY stock-front/package.json ./
COPY stock-front/package-lock.json ./

RUN if [ -f package-lock.json ]; then npm ci --silent; else npm install --silent; fi

# Copy source and build
COPY stock-front/ ./
# Allow overriding VITE_API_BASE at build time; default is empty so frontend will call relative /api paths
ARG VITE_API_BASE=""
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build


# Stage 2: runtime with Python backend
FROM python:3.11-slim
WORKDIR /app

# Install python deps
COPY back/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend sources
COPY back/ ./back
WORKDIR /app/back

# Copy built frontend into backend static folder
COPY --from=build-frontend /app/stock-front/dist ./static

ENV PORT=8000
EXPOSE 8000

# Use uvicorn to run the FastAPI app and respect Railway's $PORT env var
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

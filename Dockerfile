# Multi-stage build for full-stack app
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY src/frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY src/frontend/ ./

# Build frontend (use relative URL for same-domain deployment)
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Stage 2: Python backend with frontend
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY src/backend /app/src/backend

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/dist /app/src/frontend/dist

# Create data directory for cache
RUN mkdir -p /app/data

# Expose port (will be set by PORT env var at runtime)
EXPOSE 8000

# Set Python path
ENV PYTHONPATH=/app

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Run the application (use PORT env var if set, default to 8000)
CMD ["/app/start.sh"]


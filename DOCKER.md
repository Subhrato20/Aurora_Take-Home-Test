# Docker Setup Guide

This guide explains how to build and run the Aurora Take-Home Test application using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose installed (usually comes with Docker Desktop)
- An OpenAI API key

## Quick Start

1. **Set up environment variables**

   Create a `.env` file in the root directory with the following variables:

   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o-mini
   NOVEMBER_API_BASE=https://november7-730026606190.europe-west1.run.app
   PAGE_SIZE=100
   MAX_VALIDATOR_MESSAGES=12
   NAME_RESOLVER_MAX_NAMES=50
   ```

2. **Build and run with Docker Compose**

   ```bash
   docker-compose up --build
   ```

   This will:
   - Build both backend and frontend containers
   - Start the backend on port 8000
   - Start the frontend on port 3000
   - Mount the `data/` directory for persistent cache storage

3. **Access the application**

   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Building Individual Containers

### Backend Only

```bash
docker build -f Dockerfile.backend -t aurora-backend .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -v $(pwd)/data:/app/data \
  aurora-backend
```

### Frontend Only

```bash
docker build -f Dockerfile.frontend -t aurora-frontend \
  --build-arg VITE_API_BASE_URL=http://localhost:8000 .
docker run -p 3000:80 aurora-frontend
```

## Production Considerations

For production deployment:

1. **Update CORS settings** in `src/backend/main.py` to allow your production frontend domain
2. **Set VITE_API_BASE_URL** during frontend build to point to your production backend URL
3. **Use environment-specific .env files** or secrets management
4. **Consider using a reverse proxy** (nginx/traefik) in front of both services
5. **Set up proper logging and monitoring**

## Troubleshooting

- **Backend won't start**: Check that `OPENAI_API_KEY` is set correctly
- **Frontend can't connect to backend**: Verify `VITE_API_BASE_URL` matches your backend URL
- **Cache not persisting**: Ensure the `data/` directory has proper permissions
- **Port conflicts**: Change ports in `docker-compose.yml` if 8000 or 3000 are already in use

## Stopping the Application

```bash
docker-compose down
```

To also remove volumes:

```bash
docker-compose down -v
```


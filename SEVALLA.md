# Sevalla Deployment Guide

## Configuration Checklist

1. **Health Check Path**: Set to `/health` in Sevalla dashboard
   - Go to: Settings > Health Check
   - Path: `/health`
   - Expected response: `{"status": "healthy"}`

2. **Port Configuration**: 
   - Container listens on port `8000`
   - Sevalla will map this automatically
   - Ensure `PORT=8000` is set in environment variables

3. **Environment Variables** (Required):
   - `OPENAI_API_KEY` - Your OpenAI API key (required)
   - `PORT=8000` - Port the app listens on (set automatically by Sevalla)

4. **Environment Variables** (Optional):
   - `OPENAI_MODEL` - Default: `gpt-4o-mini`
   - `NOVEMBER_API_BASE` - Default: `https://november7-730026606190.europe-west1.run.app`
   - `PAGE_SIZE` - Default: `100`
   - `MAX_VALIDATOR_MESSAGES` - Default: `12`
   - `NAME_RESOLVER_MAX_NAMES` - Default: `50`

## Troubleshooting 503 Errors

If you're getting 503 errors:

1. **Check Health Check**: 
   - Verify `/health` endpoint returns `{"status": "healthy"}`
   - Check if health check path is set correctly in Sevalla dashboard

2. **Check Logs**:
   - Look for "🚀 Starting Aurora Q&A Service..."
   - Check for "✅ Imports successful"
   - Look for any Python errors

3. **Verify Environment Variables**:
   - Ensure `OPENAI_API_KEY` is set
   - Check that `PORT` is set (Sevalla usually sets this automatically)

4. **Check Service Status**:
   - Visit `https://your-app.sevalla.app/health` directly
   - Should return: `{"status": "healthy"}`

## Build Configuration

- **Build Path**: `.` (root)
- **Dockerfile**: `Dockerfile`
- **Docker Compose**: `docker-compose.yml`

The app builds the frontend during Docker build and serves it from the same FastAPI backend.


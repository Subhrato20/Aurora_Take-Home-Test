# Frontend-Backend Connection Guide

## Overview

The frontend is now connected to the FastAPI backend Q&A service. The integration allows users to ask questions through the UI and receive answers from the November messages API.

## Architecture

### Backend (FastAPI)
- **Port**: 8000 (default)
- **Endpoint**: `POST /ask`
- **Request**: `{ "question": "string" }`
- **Response**: `{ "answer": "string", "message": {...} }`
- **CORS**: Enabled for frontend origins

### Frontend (React + Vite)
- **Port**: 5173 (default)
- **API Client**: `src/lib/api.ts`
- **Main Component**: `src/components/qa-chat.tsx`

## Setup Instructions

### 1. Backend Setup

Make sure the backend is running:

```bash
cd /Users/subhratosom/Aurora_Take-Home-Test
export OPENAI_API_KEY=your-api-key-here
PYTHONPATH=src uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

The frontend will automatically connect to `http://localhost:8000` by default.

To use a different backend URL, create a `.env` file in `src/frontend/`:

```bash
cd src/frontend
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
```

Then start the frontend:

```bash
npm run dev
```

### 3. Testing the Connection

1. Start the backend server (port 8000)
2. Start the frontend dev server (port 5173)
3. Open `http://localhost:5173` in your browser
4. Type a question like "When is Layla's next trip?"
5. The question will be sent to the backend and the answer will be displayed

## Features

### QAChat Component

The `QAChat` component provides:
- **Chat Interface**: Messages displayed in a conversation format
- **Loading States**: Shows "Thinking..." while waiting for response
- **Error Handling**: Displays error messages if the API call fails
- **Message History**: Keeps track of all questions and answers
- **Special Modes**: Supports Search, Think, and Canvas prefixes from PromptInputBox

### API Client

The `askQuestion` function in `src/lib/api.ts`:
- Handles HTTP requests to the backend
- Manages error responses
- Returns typed responses matching the backend schema

## CORS Configuration

The backend is configured to allow requests from:
- `http://localhost:5173` (Vite default)
- `http://localhost:3000` (alternative React dev server)
- `http://127.0.0.1:5173` (alternative localhost format)

To add more origins, edit `src/backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "https://your-production-domain.com"  # Add production URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Connection Refused
- Ensure the backend is running on port 8000
- Check that no firewall is blocking the connection
- Verify the `VITE_API_BASE_URL` environment variable if using a custom URL

### CORS Errors
- Make sure the frontend origin is in the backend's CORS allowed origins
- Check browser console for specific CORS error messages

### API Errors
- Check backend logs for detailed error information
- Verify that `OPENAI_API_KEY` is set in the backend environment
- Ensure the November API is accessible

## Development Workflow

1. **Backend Changes**: Restart the uvicorn server to apply changes
2. **Frontend Changes**: Vite will hot-reload automatically
3. **API Changes**: Update both `src/backend/schemas.py` and `src/frontend/src/lib/api.ts` to keep types in sync


# Quick Start Guide - Frontend & Backend Connection

## Prerequisites

- Python 3.12+ with virtual environment
- Node.js and npm installed
- OpenAI API key

## Starting the Application

### 1. Start the Backend

```bash
# Navigate to project root
cd /Users/subhratosom/Aurora_Take-Home-Test

# Activate virtual environment (if using one)
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Set OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Start the backend server
PYTHONPATH=src uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

### 2. Start the Frontend

Open a new terminal:

```bash
# Navigate to frontend directory
cd /Users/subhratosom/Aurora_Take-Home-Test/src/frontend

# Install dependencies (first time only)
npm install

# Start the development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### 3. Use the Application

1. Open `http://localhost:5173` in your browser
2. Type a question in the input box, for example:
   - "When is Layla's next trip?"
   - "How many cars does Layla have?"
   - "What are Layla's upcoming events?"
3. Press Enter or click the send button
4. Wait for the AI to process your question and return an answer

## Features

- **Chat Interface**: Clean, modern chat UI with message history
- **Loading States**: Visual feedback while processing questions
- **Error Handling**: Clear error messages if something goes wrong
- **Special Modes**: Use Search, Think, or Canvas modes from the input box
- **Responsive Design**: Works on different screen sizes

## Troubleshooting

### Backend not responding
- Check that the backend is running on port 8000
- Verify `OPENAI_API_KEY` is set correctly
- Check backend terminal for error messages

### Frontend can't connect
- Ensure backend is running first
- Check browser console for CORS errors
- Verify both servers are running on correct ports

### API Errors
- Check that OpenAI API key is valid
- Verify November API is accessible
- Check backend logs for detailed error information

## Development

- **Backend changes**: Restart uvicorn server
- **Frontend changes**: Vite hot-reloads automatically
- **API changes**: Update both backend schemas and frontend types

## Project Structure

```
Aurora_Take-Home-Test/
├── src/
│   ├── backend/          # FastAPI backend
│   │   └── main.py       # API endpoints
│   └── frontend/         # React frontend
│       └── src/
│           ├── components/
│           │   ├── ui/   # UI components (shadcn)
│           │   └── qa-chat.tsx  # Main chat component
│           └── lib/
│               └── api.ts  # API client
└── data/                 # Cache and data files
```


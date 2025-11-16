#!/bin/bash
set -e

echo "🚀 Starting Aurora Q&A Service..."
echo "PORT: ${PORT:-8000}"
echo "PYTHONPATH: ${PYTHONPATH}"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:+SET}"

# Start the server
exec uvicorn src.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}


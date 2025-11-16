#!/bin/bash
set -e

echo "🚀 Starting Aurora Q&A Service..."
echo "PORT: ${PORT:-8000}"
echo "PYTHONPATH: ${PYTHONPATH:-not set}"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:+SET (hidden)}${OPENAI_API_KEY:-NOT SET}"

# Verify Python can import the module
echo "Testing Python imports..."
python3 -c "import sys; sys.path.insert(0, '/app'); from src.backend import main; print('✅ Imports successful')" || {
    echo "❌ Import failed!"
    exit 1
}

# Start the server
echo "Starting uvicorn server..."
exec uvicorn src.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}


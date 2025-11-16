#!/bin/bash
# Build script for Render deployment
# Builds frontend (dependencies should already be installed by nixpacks)

# Don't exit on error - we want server to start even if frontend build fails
set +e

echo "Node.js version: $(node --version || echo 'Node.js not found')"
echo "npm version: $(npm --version || echo 'npm not found')"
echo "Python version: $(python3 --version || echo 'Python not found')"

echo "📦 Building frontend..."
cd src/frontend

# Install dependencies (nixpacks should have run npm ci, but ensure it's done)
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm ci || echo "⚠️  npm ci failed, continuing..."
fi

# Build the frontend
echo "Building React app..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Frontend build successful!"
    echo "Frontend built in: src/frontend/dist"
else
    echo "⚠️  Frontend build failed, but continuing with backend..."
fi

cd ../..

echo "✅ Build script complete - starting server..."


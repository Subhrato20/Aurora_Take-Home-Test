#!/bin/bash
# Build script for Render deployment
# Builds frontend (dependencies should already be installed by nixpacks)

set -e

echo "📦 Building frontend..."
cd src/frontend

# Install dependencies if node_modules doesn't exist (fallback)
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm ci
fi

# Build the frontend
echo "Building React app..."
npm run build

cd ../..

echo "✅ Build complete!"
echo "Frontend built in: src/frontend/dist"


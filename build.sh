#!/bin/bash
# Build script for Render deployment
# Builds frontend (dependencies should already be installed by nixpacks)

set -e

echo "Node.js version: $(node --version || echo 'Node.js not found')"
echo "npm version: $(npm --version || echo 'npm not found')"

echo "📦 Building frontend..."
cd src/frontend

# Install dependencies (nixpacks should have run npm ci, but ensure it's done)
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm ci
fi

# Build the frontend
echo "Building React app..."
npm run build

cd ../..

echo "✅ Build complete!"
echo "Frontend built in: src/frontend/dist"


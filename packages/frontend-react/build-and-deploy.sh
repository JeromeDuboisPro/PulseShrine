#!/bin/bash

# PulseShrine Frontend - Build and Deploy Script
# This script builds the React frontend and copies it to replace the vanilla JS frontend

set -e  # Exit on any error

echo "🏗️  Building PulseShrine React Frontend..."

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Make sure you're in the frontend-react directory."
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Check if environment variables are set
if [ -z "$VITE_API_KEY" ] && [ ! -f ".env.local" ]; then
    echo "⚠️  Warning: No environment variables detected."
    echo "   Please either:"
    echo "   1. Set VITE_API_KEY and VITE_API_BASE_URL environment variables, or"
    echo "   2. Create a .env.local file with your API configuration"
    echo "   3. Use the configuration UI after starting the app"
    echo ""
fi

# Build the project
echo "🔨 Building production bundle..."
npm run build

# Check if build was successful
if [ ! -d "dist" ]; then
    echo "❌ Build failed - dist directory not created"
    exit 1
fi

echo "✅ Build completed successfully!"
echo "📁 Built files are in the 'dist' directory"

# Start the preview server
echo ""
echo "🚀 Starting preview server..."
echo "📋 The React frontend will be available at: http://localhost:4173"
echo "⚡ Press Ctrl+C to stop the server"
echo ""

npm run preview
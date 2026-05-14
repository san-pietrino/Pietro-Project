#!/bin/bash

# Pietro - Start Script
# This script starts the Pietro peer-to-peer lending web app

echo "🔧 Starting Pietro..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo "   Please install Python from https://www.python.org/"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ] && [ ! -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip3 install -r requirements.txt
fi

# Change to script directory
cd "$(dirname "$0")"

# Start the Flask app in background
echo "🚀 Starting Flask server..."
python3 app.py &
APP_PID=$!

echo ""
echo "✅ Pietro is running!"
echo ""
echo "📍 Open your browser and go to:"
echo "   http://127.0.0.1:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Wait for the process
wait $APP_PID
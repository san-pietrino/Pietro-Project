#!/bin/bash

# Pietro - Stop Script
# This script stops the Pietro web app

echo "🛑 Stopping Pietro..."

# Find and kill the Flask process
APP_PID=$(ps aux | grep "python3 app.py" | grep -v grep | awk '{print $2}')

if [ -n "$APP_PID" ]; then
    kill $APP_PID
    echo "✅ Pietro has been stopped."
else
    echo "⚠️  No running Pietro process found."
fi

echo ""
echo "👋 Goodbye!"
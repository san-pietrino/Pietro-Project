@echo off
REM Pietro - Start Script (Windows)
REM This script starts the Pietro peer-to-peer lending web app

echo 🔧 Starting Pietro...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed.
    echo    Please install Python from https://www.python.org/
    echo    Or run: winget install Python.Python.3.12
    exit /b 1
)

REM Install dependencies if needed
echo 📦 Installing Python dependencies...
pip install -r requirements.txt

REM Change to script directory
cd /d "%~dp0"

REM Start the Flask app
echo 🚀 Starting Flask server...
start "Pietro" python app.py

echo.
echo ✅ Pietro is running!
echo.
echo 📍 Open your browser and go to:
echo    http://127.0.0.1:5000
echo.
echo Press Ctrl+C in the Flask window to stop the server
echo.

REM Open browser
start http://127.0.0.1:5000
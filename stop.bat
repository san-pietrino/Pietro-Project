@echo off
REM Pietro - Stop Script (Windows)
REM This script stops the Pietro web app

echo 🛑 Stopping Pietro...

REM Find and kill the Python process running app.py
taskkill /F /FI "WINDOWTITLE eq Pietro*" >nul 2>&1

echo ✅ Pietro has been stopped.
echo.
echo 👋 Goodbye!
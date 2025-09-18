@echo off
echo Stopping any existing Python processes...
taskkill /f /im python.exe 2>nul
timeout /t 2 /nobreak >nul

echo Starting Flask server...
python main.py
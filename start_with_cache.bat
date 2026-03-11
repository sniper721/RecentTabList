@echo off
echo ================================================================================
echo INSTANT LOAD - Auto Pre-load Cache and Start Server
echo ================================================================================
echo.
echo This will:
echo   1. Pre-load all levels from database (takes 1-2 minutes)
echo   2. Save to JSON cache files
echo   3. Start server with instant loading
echo.
echo Press Ctrl+C at any time to cancel
echo.
pause
echo.

python auto_preload_and_start.py

pause

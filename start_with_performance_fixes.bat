@echo off
echo ================================================================================
echo STARTING SERVER WITH PERFORMANCE FIXES
echo ================================================================================
echo.

echo [1/3] Clearing cache and optimizing...
python fix_slow_loading.py
if errorlevel 1 (
    echo WARNING: Optimization script had issues, continuing anyway...
)
echo.

echo [2/3] Starting main server...
echo Press Ctrl+C to stop the server
echo.
echo ================================================================================
echo.

python main.py

pause

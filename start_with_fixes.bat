@echo off
echo ======================================================================
echo Starting RTL with MongoDB Timeout Fixes
echo ======================================================================
echo.
echo Changes Applied:
echo   - MongoDB timeouts increased to 30-45 seconds
echo   - Level monitor starts after 30 second delay (non-blocking)
echo   - Better error handling for connection issues
echo.
echo Expected Behavior:
echo   - Initial startup: 20-30 seconds (normal)
echo   - Page loads: Fast after initial connection
echo   - Level monitor: Runs in background without blocking
echo.
echo Monitoring:
echo   - Watch console for "MongoDB initialized successfully"
echo   - Level monitor will start after 30 second delay
echo   - Any timeout errors will be logged but won't crash the site
echo.
echo ======================================================================
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start the main application
echo Starting main.py...
python main.py

pause

@echo off
echo ================================================================================
echo INSTANT LOAD - Pre-loading cache before server start
echo ================================================================================
echo.

echo [Step 1/2] Pre-loading levels from database (this may take 1-2 minutes)...
python preload_cache.py

if errorlevel 1 (
    echo.
    echo WARNING: Cache pre-load had issues, but continuing anyway...
)

echo.
echo [Step 2/2] Starting server with cached data...
echo.
echo ================================================================================
echo.
echo The website should now load INSTANTLY!
echo Press Ctrl+C to stop the server
echo.
echo ================================================================================
echo.

python main.py

pause

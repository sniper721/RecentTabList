@echo off
echo 🚀 Starting RTL Website - Enhanced MongoDB Version
echo.
echo This version includes:
echo - Multiple MongoDB connection strategies
echo - Automatic fallback to localhost
echo - Better error handling and recovery
echo - Health monitoring endpoint
echo - Manual reconnect capability
echo.
echo Access Points:
echo - Website: http://localhost:10000
echo - Health Check: http://localhost:10000/health
echo - Test Page: http://localhost:10000/test
echo - Manual Reconnect: http://localhost:10000/reconnect
echo.
echo Press Ctrl+C to stop the server
echo.
python main_enhanced.py
pause
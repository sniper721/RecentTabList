@echo off
echo 🎯 RTL Performance Test
echo ======================
echo.
echo Testing performance improvements...
echo.
echo 1. Health Check Response Time:
powershell -Command "Measure-Command { curl -Uri 'http://localhost:10000/health' -UseBasicParsing } | Select-Object TotalMilliseconds"
echo.
echo 2. Main Page Load Time:
powershell -Command "Measure-Command { curl -Uri 'http://localhost:10000/' -UseBasicParsing -TimeoutSec 10 } | Select-Object TotalMilliseconds"
echo.
echo 3. Performance Features Active:
curl -Uri 'http://localhost:10000/health' -UseBasicParsing | Select-Object -ExpandProperty Content
echo.
echo Performance optimizations include:
echo - Database indexes for faster queries
echo - 2-minute caching for level data
echo - Background processing for heavy operations
echo - Batch operations for bulk actions
echo - Optimized admin panel queries
echo.
pause
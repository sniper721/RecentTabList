@echo off
echo 🎯 RTL Ultra-Fast Performance Test
echo ==================================
echo.
echo Testing ultra-fast optimizations...
echo.
echo 1. System Health Check:
curl -Uri 'http://localhost:10000/health' -UseBasicParsing | Select-Object -ExpandProperty Content
echo.
echo 2. Cache Status:
curl -Uri 'http://localhost:10000/admin/cache/stats' -UseBasicParsing | Select-Object -ExpandProperty Content
echo.
echo 3. Admin Dashboard Load Time:
powershell -Command "Measure-Command { curl -Uri 'http://localhost:10000/admin' -UseBasicParsing -TimeoutSec 5 } | Select-Object TotalMilliseconds"
echo.
echo 4. Level Management Load Time:
powershell -Command "Measure-Command { curl -Uri 'http://localhost:10000/admin/levels' -UseBasicParsing -TimeoutSec 5 } | Select-Object TotalMilliseconds"
echo.
echo 5. Main Page Load Time:
powershell -Command "Measure-Command { curl -Uri 'http://localhost:10000/' -UseBasicParsing -TimeoutSec 5 } | Select-Object TotalMilliseconds"
echo.
echo 🚀 Ultra-Fast Features Active:
echo - 5-minute intelligent caching
echo - Background cache preloading (100 levels each)
echo - Paginated level management (50 per page)
echo - Instant level operations
echo - No file system checks
echo - Minimal database queries
echo.
pause
@echo off
title ChatCore - Starting...
cd /d "%~dp0"
echo ========================================
echo    ChatCore - Starting All Services
echo ========================================
echo.

echo [1/2] Starting Docker containers...
docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker compose failed!
    pause
    exit /b 1
)
echo [OK] Docker containers started
echo.

echo [2/2] Checking backend health...
:wait
timeout /t 3 /nobreak >nul
curl -s http://localhost:8000/healthz >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto wait
echo [OK] Backend is running on http://localhost:8000
echo.

echo ========================================
echo    All Services Running!
echo.
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:3000
echo    API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press any key to view container status...
pause >nul
docker ps --format "table {{.Names}}\t{{.Status}}"
echo.
pause
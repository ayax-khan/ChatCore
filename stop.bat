@echo off
title ChatCore - Stopping...
cd /d "%~dp0"
echo ========================================
echo    ChatCore - Stopping All Services
echo ========================================
echo.
docker compose down
echo.
echo [OK] All containers stopped.
echo.
pause
@echo off
echo === Starting Backend (port 8000) ===
start "CaseLens-Backend" cmd /k "cd /d %~dp0apps\search-api && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo === Starting Frontend (port 3000) ===
start "CaseLens-Frontend" cmd /k "cd /d %~dp0apps\web && set NODE_OPTIONS=--dns-result-order=ipv4first && npx next dev --port 3000"

echo.
echo Both servers starting in separate windows.
echo Frontend: http://127.0.0.1:3000
echo Backend:  http://127.0.0.1:8000
echo.
pause

@echo off
setlocal

set DOCKER="C:\Program Files\Docker\Docker\resources\bin\docker.exe"

echo =========================================
echo Entity CRUD - Rebuild and Test Script
echo =========================================
echo.

REM Step 1: Stop containers
echo [1/6] Stopping existing containers...
%DOCKER% compose -f docker-compose.e2e.yml down
if errorlevel 1 (
    echo ERROR: Failed to stop containers
    exit /b 1
)
echo Done: Containers stopped
echo.

REM Step 2: Rebuild frontend
echo [2/6] Rebuilding frontend container (no cache)...
%DOCKER% compose -f docker-compose.e2e.yml build --no-cache web
if errorlevel 1 (
    echo ERROR: Failed to build frontend
    exit /b 1
)
echo Done: Frontend rebuilt
echo.

REM Step 3: Start services
echo [3/6] Starting all services...
%DOCKER% compose -f docker-compose.e2e.yml up -d
if errorlevel 1 (
    echo ERROR: Failed to start services
    exit /b 1
)
echo Done: Services started
echo.

REM Step 4: Wait for services
echo [4/6] Waiting for services to be ready (30 seconds)...
timeout /t 30 /nobreak >nul
echo Done: Wait complete
echo.

REM Step 5: Verify services
echo [5/6] Verifying services...
curl -s http://localhost:8001/health
echo.
curl -s -I http://localhost:3001 | findstr "HTTP"
echo.

REM Step 6: Run tests
echo [6/6] Running entity CRUD tests...
echo =========================================
cd e2e
set BASE_URL=http://localhost:3001
set API_URL=http://localhost:8001
npx playwright test tests/entities/crud.spec.ts

echo.
echo =========================================
echo Test run complete!
echo =========================================

@echo off
setlocal

:: Configuration
set OM_DIR=..\openmetadata-docker
set BACKEND_DIR=backend
set FRONTEND_DIR=frontend
set ENV_FILE=.env

echo [INFO] Starting Auto-Classification App on Windows...

:: Check for Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH. Please install Docker Desktop.
    exit /b 1
)

:: Start Infrastructure
echo [INFO] Starting Infrastructure (Docker)...
if exist "%OM_DIR%" (
    cd "%OM_DIR%"
    docker compose -f docker-compose-postgres.yml up -d
    cd ..\auto-classification-app
) else (
    echo [ERROR] OpenMetadata directory not found.
    exit /b 1
)

:: Wait for OpenMetadata
echo [INFO] Waiting for OpenMetadata to be ready (may take a few minutes)...
:wait_loop
timeout /t 5 /nobreak >nul
curl -s http://localhost:8585/api/v1/system/config/auth >nul 2>&1
if %errorlevel% neq 0 (
    echo Waiting...
    goto wait_loop
)
echo [SUCCESS] OpenMetadata is online!

:: Start Data Sources
if exist "docker-compose-sources.yaml" (
    docker compose -f docker-compose-sources.yaml up -d
)

:: Backend Setup
cd backend
if not exist "venv" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate
echo [INFO] Installing Backup dependencies...
pip install -r requirements.txt >nul 2>&1
python -m spacy download en_core_web_lg >nul 2>&1

:: Generate Token (Simplified Windows Version)
echo [INFO] Generating Token...
for /f "tokens=*" %%i in ('python generate_token.py') do set TOKEN=%%i
python -c "import os; open('app/integration/om_client.py', 'r').read().replace('os.getenv(\"OPENMETADATA_TOKEN\", \"\")', 'os.getenv(\"OPENMETADATA_TOKEN\", \"%TOKEN%\")')"

:: Start Backend
start "Backend API" cmd /k "venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
cd ..

:: Frontend Setup
cd frontend
if not exist "node_modules" (
    echo [INFO] Installing Frontend Dependencies...
    call npm install
)

:: Start Frontend
start "Frontend UI" cmd /k "npm run dev -- --host --port 3000"
cd ..

echo [SUCCESS] Application Started!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo OpenMetadata: http://localhost:8585

endlocal

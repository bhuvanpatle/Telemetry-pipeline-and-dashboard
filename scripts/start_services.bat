@echo off
REM Start all services for the telemetry pipeline (Windows version)

echo Starting Telemetry Pipeline Services...

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running. Please start Docker Desktop.
    exit /b 1
)

REM Start Docker services
echo Starting Docker Compose services...
docker-compose up -d

REM Wait for services to be ready
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Check service health
echo Checking service health...

REM Check Mosquitto
docker ps | find "mosquitto" >nul
if %errorlevel% equ 0 (
    echo √ Mosquitto MQTT broker is running
) else (
    echo × Mosquitto MQTT broker failed to start
)

REM Check InfluxDB
docker ps | find "influxdb" >nul
if %errorlevel% equ 0 (
    echo √ InfluxDB is running
) else (
    echo × InfluxDB failed to start
)

REM Check Grafana
docker ps | find "grafana" >nul
if %errorlevel% equ 0 (
    echo √ Grafana is running
) else (
    echo × Grafana failed to start
)

echo.
echo Services are starting up. Please wait a moment for full initialization.
echo.
echo Access URLs:
echo   - Grafana:  http://localhost:3000 (admin/admin)
echo   - InfluxDB: http://localhost:8086
echo   - MQTT:     localhost:1883 (MQTT), localhost:9001 (WebSocket)
echo.
echo To start the Python services:
echo   python collector/ingest.py          # Start telemetry collector
echo   python simulator/ahu_simulator.py   # Start AHU simulator  
echo   python backend/status.py            # Start status API
echo.
echo To stop all services:
echo   docker-compose down

pause

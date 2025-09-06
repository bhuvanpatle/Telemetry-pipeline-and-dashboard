#!/bin/bash
# Start all services for the telemetry pipeline

echo "Starting Telemetry Pipeline Services..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Start Docker services
echo "Starting Docker Compose services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check service health
echo "Checking service health..."

# Check Mosquitto
if docker ps | grep -q mosquitto; then
    echo "✓ Mosquitto MQTT broker is running"
else
    echo "✗ Mosquitto MQTT broker failed to start"
fi

# Check InfluxDB
if docker ps | grep -q influxdb; then
    echo "✓ InfluxDB is running"
else
    echo "✗ InfluxDB failed to start"
fi

# Check Grafana
if docker ps | grep -q grafana; then
    echo "✓ Grafana is running"
else
    echo "✗ Grafana failed to start"
fi

echo ""
echo "Services are starting up. Please wait a moment for full initialization."
echo ""
echo "Access URLs:"
echo "  - Grafana:  http://localhost:3000 (admin/admin)"
echo "  - InfluxDB: http://localhost:8086"
echo "  - MQTT:     localhost:1883 (MQTT), localhost:9001 (WebSocket)"
echo ""
echo "To start the Python services:"
echo "  python collector/ingest.py          # Start telemetry collector"
echo "  python simulator/ahu_simulator.py   # Start AHU simulator"
echo "  python backend/status.py            # Start status API"
echo ""
echo "To stop all services:"
echo "  docker-compose down"

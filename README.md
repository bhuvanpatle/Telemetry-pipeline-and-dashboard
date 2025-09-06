# Building Telemetry Pipeline and Dashboard

A complete end-to-end telemetry pipeline for building management systems featuring HVAC simulation, real-time data collection, time-series storage, and interactive dashboards.

## 🏗️ Architecture Overview

```
┌─────────────────┐    MQTT     ┌─────────────────┐    InfluxDB    ┌─────────────────┐
│ AHU Simulator   │────────────▶│ Mosquitto MQTT │────────────────▶│   InfluxDB      │
│ (DDC Logic)     │             │    Broker       │                │ (Time Series)   │
└─────────────────┘             └─────────────────┘                └─────────────────┘
                                         │                                   │
┌─────────────────┐                     │                                   │
│ BDG Replay Tool │─────────────────────┘                                   │
│ (Historical)    │                                                         │
└─────────────────┘                                                         │
                                                                             │
┌─────────────────┐    REST API                    ┌─────────────────┐     │
│ React Frontend  │◀───────────┐                   │    Grafana      │◀────┘
│ (Dashboard)     │             │                   │  (Dashboards)   │
└─────────────────┘             │                   └─────────────────┘
         │                      │
         └─── WebSocket ─────────┼──────────────────────────────────────────┘
                                │
                        ┌─────────────────┐
                        │ FastAPI Backend │
                        │ (Status/Control)│
                        └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Windows 11 with Docker Desktop
- Python 3.10+
- Node.js 18+
- Git

### One-Command Setup

```bash
# 1. Clone and setup
git clone https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard.git
cd Telemetry-pipeline-and-dashboard
cp .env.example .env

# 2. Start infrastructure
docker-compose up -d

# 3. Start Python services (in separate terminals)
python collector/ingest.py
python simulator/ahu_simulator.py
python backend/status.py

# 4. Access dashboards
# Grafana: http://localhost:3000 (admin/admin)
# React Dashboard: http://localhost:3001
```

### Windows Quick Start Script

```cmd
scripts\start_services.bat
```

## 📦 Components

### 1. AHU Simulator (`simulator/`)

Sophisticated Air Handling Unit simulator with DDC control logic:

- **PID Temperature Control**: Maintains supply air temperature
- **Economizer Logic**: Free cooling when outside conditions permit
- **VFD Speed Control**: Variable frequency drive for fan control
- **Alarm Generation**: Fault detection and alerting
- **Weather Integration**: Real weather data via Open-Meteo API

```bash
# Run simulator
python simulator/ahu_simulator.py --mode live --cadence 2

# Configuration
simulator/config.yaml
```

### 2. MQTT → InfluxDB Collector (`collector/`)

High-performance telemetry ingestion service:

- Subscribes to `building/#` MQTT topics
- Parses JSON telemetry payloads
- Writes time-series data to InfluxDB
- Configurable via YAML

```bash
# Run collector
python collector/ingest.py --config collector/config.yaml
```

### 3. Building Data Genome Replay (`replay/`)

Historical data replay for commissioning scenarios:

- Reads BDG Project CSV files
- Accelerated playback (1x to 100x speed)
- Generates sample datasets
- Publishes to MQTT with original timestamps

```bash
# Replay historical data
python replay/replay_bdg.py --file "Building Data Genome Project 2/electricity.csv" --speed 10

# Create sample files
python replay/replay_bdg.py --create-samples --sample-rows 1000
```

### 4. REST API Backend (`backend/`)

FastAPI service for dashboard integration:

- Health monitoring endpoints
- Last-value queries from InfluxDB
- Replay control (start/stop)
- CORS-enabled for frontend access

```bash
# Run backend API
python backend/status.py

# API Documentation: http://localhost:8000/docs
```

### 5. React Dashboard (`frontend/`)

Modern single-page application with dual modes:

- **Live Mode**: Real-time MQTT WebSocket connection
- **Demo Mode**: Static data for GitHub Pages deployment
- Interactive charts (Chart.js)
- Alarm management
- CSV export functionality

```bash
# Development
cd frontend
npm install
npm run dev

# Production build
npm run build
```

### 6. Grafana Dashboards (`grafana/`)

Pre-configured dashboards for operations teams:

- Temperature control trends
- VFD performance monitoring
- Energy consumption analysis
- Alarm visualization
- Auto-provisioned data sources

## 🔧 Configuration

### Environment Variables

```bash
# Copy and customize
cp .env.example .env

# Key settings
INFLUXDB_TOKEN=your-token-here
MQTT_BROKER=localhost
GRAFANA_PASSWORD=admin
```

### MQTT Topics

```
building/{building_id}/{device_id}/telemetry
```

### JSON Payload Schema

```json
{
  "ts": 1690000000000,
  "device": "ahu1",
  "building": "demo_building",
  "points": {
    "outside_temp": 29.4,
    "supply_temp": 18.2,
    "setpoint": 18.0,
    "vfd_speed": 54.1,
    "fan_status": "ON",
    "alarm": null
  }
}
```

## 🧪 Testing

### Factory Acceptance Tests

```bash
# Run comprehensive FAT suite
cd FAT_tests
python test_ahu_logic.py

# Using pytest
pytest FAT_tests/ -v --cov
```

Test coverage includes:

- PID controller behavior
- Economizer control logic
- Temperature stability
- Alarm generation
- Telemetry format validation

### CI/CD Pipeline

GitHub Actions workflow automatically:

- Runs linting (flake8)
- Executes test suite
- Builds Docker containers
- Deploys frontend to GitHub Pages

## 🚢 Deployment

### Local Development

1. Start Docker services: `docker-compose up -d`
2. Run Python services individually
3. Access dashboards via localhost

### GitHub Pages Deployment

```bash
# Build and deploy frontend
cd frontend
npm run build
npm run deploy
```

### Production Deployment

- Use environment-specific `.env` files
- Configure proper authentication
- Setup SSL/TLS certificates
- Scale services with Docker Swarm/Kubernetes

## 📊 Performance

### Metrics

- **Telemetry Rate**: 0.5-2 Hz per device
- **Response Time**: <100ms control loop
- **Memory Usage**: <50MB per simulator
- **Data Retention**: Configurable in InfluxDB

### Scaling

- Horizontal scaling via MQTT load balancing
- InfluxDB clustering for high availability
- Multiple collector instances for redundancy

## 🔍 Monitoring

### Service Health

```bash
# Check all services
curl http://localhost:8000/health

# MQTT connectivity
mosquitto_pub -h localhost -t test/topic -m "hello"

# InfluxDB queries
curl "http://localhost:8086/api/v2/query" -H "Authorization: Token your-token"
```

### Grafana Dashboards

- Building overview
- Energy consumption trends
- HVAC performance metrics
- System health monitoring

## 📁 Project Structure

```
├── simulator/              # AHU simulator with DDC logic
├── collector/              # MQTT → InfluxDB ingestion
├── replay/                 # Historical data replay tools
├── backend/                # REST API service
├── frontend/               # React dashboard SPA
├── grafana/                # Dashboard and data source configs
├── FAT_tests/              # Factory acceptance tests
├── scripts/                # Automation and utility scripts
├── docs/                   # Additional documentation
├── docker-compose.yml      # Container orchestration
└── .github/workflows/      # CI/CD automation
```

## 🔄 CI/CD Pipeline

[![CI Pipeline](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/ci.yml)
[![Deploy Frontend](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/deploy_frontend.yml/badge.svg)](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/deploy_frontend.yml)

### Automated Workflows

The repository includes comprehensive GitHub Actions workflows:

- **🧪 CI Pipeline** (`ci.yml`): Automated testing and linting

  - Python backend tests with pytest
  - Frontend build and lint checks
  - Code coverage reporting
  - Artifact generation for debugging

- **🚀 Frontend Deployment** (`deploy_frontend.yml`): GitHub Pages deployment

  - Automatic deployment on frontend changes
  - Manual deployment option via workflow dispatch
  - Production build optimization

- **📦 Release Management** (`release.yml`): Automated releases
  - Semantic version tagging (e.g., `v1.0.0`)
  - Changelog generation
  - Asset packaging and upload

### Workflow Usage

**Manual Frontend Deployment:**

```bash
# Via GitHub CLI
gh workflow run deploy_frontend.yml -f deploy_reason="Manual deployment"

# Or use the GitHub Actions UI
```

**Creating a Release:**

```bash
git tag v1.0.0
git push origin v1.0.0
```

**Viewing Workflow Results:**

- 📊 [All Workflow Runs](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions)
- 🌐 [Live Dashboard](https://bhuvanpatle.github.io/Telemetry-pipeline-and-dashboard/)
- 📥 Download artifacts from failed runs for debugging

For detailed CI/CD documentation, see [`docs/ci_cd.md`](docs/ci_cd.md).

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `pytest FAT_tests/ -v`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push branch: `git push origin feature/amazing-feature`
6. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/discussions)
- **Documentation**: `/docs` directory

## 🏷️ Version History

- **v0.1.0** - Initial release with core functionality
- **v0.2.0** - Added replay capabilities and enhanced testing
- **v1.0.0** - Production-ready with full documentation

---

**Built with ❤️ for building automation and energy management**

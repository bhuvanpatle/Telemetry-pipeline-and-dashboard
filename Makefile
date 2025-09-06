# Telemetry Pipeline and Dashboard - Makefile
# Provides convenient commands for development and deployment

.PHONY: help install start stop test build deploy clean

# Default target
help:
	@echo "Available commands:"
	@echo "  install    - Install all dependencies"
	@echo "  start      - Start all services"
	@echo "  stop       - Stop all services"
	@echo "  test       - Run tests"
	@echo "  build      - Build frontend"
	@echo "  deploy     - Deploy to GitHub Pages"
	@echo "  clean      - Clean build artifacts"

# Install dependencies
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "Installing Node.js dependencies..."
	cd frontend && npm install
	@echo "Creating .env file if not exists..."
	@if not exist .env copy .env.example .env

# Start all services
start:
	@echo "Starting Docker services..."
	docker-compose up -d
	@echo "Services started. Access URLs:"
	@echo "  Grafana:  http://localhost:3000"
	@echo "  InfluxDB: http://localhost:8086"
	@echo "  Frontend: http://localhost:3001 (after npm run dev)"

# Stop all services
stop:
	@echo "Stopping Docker services..."
	docker-compose down

# Run tests
test:
	@echo "Running Factory Acceptance Tests..."
	python -m pytest FAT_tests/ -v
	@echo "Running linting..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Build frontend
build:
	@echo "Building frontend..."
	cd frontend && npm run build

# Deploy to GitHub Pages
deploy: build
	@echo "Deploying to GitHub Pages..."
	cd frontend && npm run deploy

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	if exist frontend\dist rmdir /s /q frontend\dist
	if exist .pytest_cache rmdir /s /q .pytest_cache
	if exist __pycache__ rmdir /s /q __pycache__
	docker-compose down --volumes --remove-orphans

# Development shortcuts
dev-collector:
	python collector/ingest.py

dev-simulator:
	python simulator/ahu_simulator.py --mode sim --cadence 2

dev-backend:
	python backend/status.py

dev-frontend:
	cd frontend && npm run dev

# Create sample data
samples:
	python replay/replay_bdg.py --create-samples --sample-rows 100

# Run replay
replay:
	python replay/replay_bdg.py --file replay/samples/sample_electricity.csv --speed 10

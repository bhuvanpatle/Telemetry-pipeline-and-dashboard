#!/usr/bin/env python3
"""
Quick start script for the Telemetry Pipeline and Dashboard project.
This script starts all the essential services for local development.
"""

import subprocess
import sys
import time
import os
from pathlib import Path


def run_command(command, description, background=False):
    """Run a command with description"""
    print(f"🔄 {description}...")
    if background:
        return subprocess.Popen(command, shell=True)
    else:
        result = subprocess.run(command, shell=True,
                                capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return result
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return None


def main():
    """Main startup sequence"""
    print("🚀 Starting Telemetry Pipeline and Dashboard Services")
    print("=" * 60)

    # Check if we're in the right directory
    if not Path("docker-compose.yml").exists():
        print("❌ Please run this script from the project root directory")
        return 1

    # Start Docker services
    print("\n📦 Starting Docker Infrastructure...")
    docker_result = run_command(
        "docker-compose up -d", "Docker services startup")
    if not docker_result:
        print("❌ Failed to start Docker services. Make sure Docker is running.")
        return 1

    # Wait for services to start
    print("⏳ Waiting for services to initialize...")
    time.sleep(10)

    # Start Python services in background
    print("\n🐍 Starting Python Services...")

    # Start AHU Simulator
    ahu_process = run_command(
        "python simulator/ahu_simulator.py",
        "AHU Simulator",
        background=True
    )

    # Start Telemetry Collector
    collector_process = run_command(
        "python collector/ingest.py",
        "Telemetry Collector",
        background=True
    )

    # Start FastAPI Backend
    backend_process = run_command(
        "python -m uvicorn backend.status:app --host 0.0.0.0 --port 8000",
        "FastAPI Backend",
        background=True
    )

    print("\n🌐 Services Started!")
    print("=" * 60)
    print("📊 Grafana Dashboard: http://localhost:3000")
    print("   Username: admin, Password: admin")
    print("📈 InfluxDB UI: http://localhost:8086")
    print("🔌 MQTT Broker: localhost:1883")
    print("🔗 FastAPI Backend: http://localhost:8000/docs")
    print("📁 Frontend (serve with local server): ./frontend/")
    print("\n💡 Tips:")
    print("   - Open Grafana and import the dashboard from grafana/dashboards/")
    print("   - Use 'python replay/replay_bdg.py' to replay building data")
    print("   - Run 'make test' to validate the system")
    print("\n⏹️  Press Ctrl+C to stop all services")

    try:
        # Keep processes running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")

        # Stop Python processes
        if 'ahu_process' in locals():
            ahu_process.terminate()
        if 'collector_process' in locals():
            collector_process.terminate()
        if 'backend_process' in locals():
            backend_process.terminate()

        # Stop Docker services
        run_command("docker-compose down", "Docker services shutdown")
        print("✅ All services stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

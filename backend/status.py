#!/usr/bin/env python3
"""
USAGE EXAMPLE:
python backend/status.py
curl http://localhost:8000/health
curl "http://localhost:8000/last?topic=building/ahu1/telemetry"
"""

import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import threading
import signal
import sys

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi
import subprocess
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
app = FastAPI(title="Telemetry Status API", version="1.0.0")
last_messages: Dict[str, Dict[str, Any]] = {}
influx_client: Optional[InfluxDBClient] = None
mqtt_client: Optional[mqtt.Client] = None
replay_process: Optional[subprocess.Popen] = None

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def setup_influxdb():
    """Setup InfluxDB client"""
    global influx_client
    try:
        influx_client = InfluxDBClient(
            url="http://localhost:8086",
            token="telemetry-token-12345",
            org="telemetry"
        )
        # Test connection
        health = influx_client.health()
        if health.status == "pass":
            logger.info("Connected to InfluxDB")
        else:
            logger.error(f"InfluxDB health check failed: {health.message}")
    except Exception as e:
        logger.error(f"Failed to connect to InfluxDB: {e}")


def setup_mqtt():
    """Setup MQTT client for real-time message tracking"""
    global mqtt_client

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker")
            client.subscribe("building/#")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")

    def on_message(client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))

            # Store last message for each topic
            last_messages[topic] = {
                "timestamp": datetime.utcnow().isoformat(),
                "topic": topic,
                "payload": payload
            }

            # Limit cache size to prevent memory issues
            if len(last_messages) > 1000:
                # Remove oldest entries
                oldest_topics = sorted(last_messages.keys(),
                                       key=lambda k: last_messages[k]["timestamp"])[:100]
                for old_topic in oldest_topics:
                    del last_messages[old_topic]

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    try:
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.connect("localhost", 1883, 60)
        mqtt_client.loop_start()
    except Exception as e:
        logger.error(f"Failed to setup MQTT client: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    setup_influxdb()
    setup_mqtt()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global influx_client, mqtt_client, replay_process

    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

    if influx_client:
        influx_client.close()

    if replay_process:
        replay_process.terminate()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "mqtt": mqtt_client.is_connected() if mqtt_client else False,
            "influxdb": influx_client is not None
        },
        "cached_topics": len(last_messages)
    }
    return status


@app.get("/last")
async def get_last_message(topic: str = Query(..., description="MQTT topic to query")):
    """Get last received message for a topic"""

    # First check in-memory cache
    if topic in last_messages:
        return last_messages[topic]

    # If not in cache, try to get from InfluxDB
    if influx_client:
        try:
            query_api = influx_client.query_api()

            # Parse topic to extract building and device
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3:
                building = topic_parts[1]
                device = topic_parts[2]

                # Query InfluxDB for last point
                query = f'''
                from(bucket: "building_data")
                  |> range(start: -24h)
                  |> filter(fn: (r) => r._measurement == "telemetry")
                  |> filter(fn: (r) => r.building == "{building}")
                  |> filter(fn: (r) => r.device == "{device}")
                  |> last()
                '''

                result = query_api.query(query)

                if result:
                    # Convert InfluxDB result to telemetry format
                    points = {}
                    timestamp = None

                    for table in result:
                        for record in table.records:
                            points[record.values["point"]] = record.get_value()
                            if not timestamp:
                                timestamp = record.get_time()

                    if points and timestamp:
                        return {
                            "timestamp": timestamp.isoformat(),
                            "topic": topic,
                            "payload": {
                                "ts": int(timestamp.timestamp() * 1000),
                                "device": device,
                                "building": building,
                                "points": points
                            }
                        }

        except Exception as e:
            logger.error(f"Error querying InfluxDB: {e}")

    raise HTTPException(
        status_code=404, detail=f"No data found for topic: {topic}")


@app.get("/topics")
async def list_topics():
    """List all topics with recent messages"""
    topics = []
    for topic, data in last_messages.items():
        topics.append({
            "topic": topic,
            "last_seen": data["timestamp"],
            "device": data["payload"].get("device", "unknown"),
            "building": data["payload"].get("building", "unknown")
        })

    # Sort by last seen (most recent first)
    topics.sort(key=lambda x: x["last_seen"], reverse=True)
    return {"topics": topics, "count": len(topics)}


@app.post("/replay/start")
async def start_replay(file_path: str = Query(...), speed: float = Query(1.0)):
    """Start replay of CSV file"""
    global replay_process

    # Stop existing replay if running
    if replay_process and replay_process.poll() is None:
        replay_process.terminate()
        replay_process.wait()

    try:
        # Build command
        cmd = [
            "python", "replay/replay_bdg.py",
            "--file", file_path,
            "--speed", str(speed),
            "--topic-prefix", "building"
        ]

        # Start replay process
        replay_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        logger.info(f"Started replay: {file_path} at {speed}x speed")

        return {
            "status": "started",
            "file_path": file_path,
            "speed": speed,
            "pid": replay_process.pid
        }

    except Exception as e:
        logger.error(f"Failed to start replay: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start replay: {e}")


@app.post("/replay/stop")
async def stop_replay():
    """Stop running replay"""
    global replay_process

    if replay_process and replay_process.poll() is None:
        try:
            replay_process.terminate()
            replay_process.wait(timeout=5)
            logger.info("Replay stopped")
            return {"status": "stopped"}
        except subprocess.TimeoutExpired:
            replay_process.kill()
            logger.warning("Replay process killed (timeout)")
            return {"status": "killed"}
    else:
        return {"status": "not_running"}


@app.get("/replay/status")
async def replay_status():
    """Get replay process status"""
    global replay_process

    if replay_process:
        if replay_process.poll() is None:
            return {
                "status": "running",
                "pid": replay_process.pid
            }
        else:
            return {
                "status": "finished",
                "return_code": replay_process.returncode
            }
    else:
        return {"status": "not_started"}


@app.get("/stats")
async def get_statistics():
    """Get telemetry statistics"""
    stats = {
        "active_topics": len(last_messages),
        "uptime_seconds": time.time() - start_time,
        "services": {
            "mqtt_connected": mqtt_client.is_connected() if mqtt_client else False,
            "influxdb_connected": influx_client is not None
        }
    }

    # Add building/device counts
    buildings = set()
    devices = set()
    for topic_data in last_messages.values():
        payload = topic_data.get("payload", {})
        buildings.add(payload.get("building", "unknown"))
        devices.add(payload.get("device", "unknown"))

    stats["unique_buildings"] = len(buildings)
    stats["unique_devices"] = len(devices)

    return stats


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)


# Track start time
start_time = time.time()

if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting Telemetry Status API server")
    uvicorn.run(app, host="0.0.0.0", port=8000)

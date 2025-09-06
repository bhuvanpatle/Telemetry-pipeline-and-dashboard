#!/usr/bin/env python3
"""
USAGE EXAMPLE:
python collector/ingest.py --config collector/config.yaml
"""

import argparse
import json
import logging
import signal
import sys
import time
from typing import Dict, Any, Optional
import yaml
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelemetryCollector:
    """MQTT to InfluxDB telemetry collector"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mqtt_client = None
        self.influx_client = None
        self.write_api = None
        self.running = False

        # Initialize connections
        self._setup_influxdb()
        self._setup_mqtt()

    def _setup_influxdb(self) -> None:
        """Setup InfluxDB client connection"""
        try:
            influx_config = self.config.get('influxdb', {})

            self.influx_client = InfluxDBClient(
                url=influx_config.get('url', 'http://localhost:8086'),
                token=influx_config.get('token', 'telemetry-token-12345'),
                org=influx_config.get('org', 'telemetry')
            )

            self.write_api = self.influx_client.write_api(
                write_options=SYNCHRONOUS)

            # Test connection
            health = self.influx_client.health()
            if health.status == "pass":
                logger.info("Connected to InfluxDB successfully")
            else:
                logger.error(f"InfluxDB health check failed: {health.message}")

        except Exception as e:
            logger.error(f"Failed to setup InfluxDB connection: {e}")

    def _setup_mqtt(self) -> None:
        """Setup MQTT client connection"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

            mqtt_config = self.config.get('mqtt', {})
            broker_host = mqtt_config.get('broker', 'localhost')
            broker_port = mqtt_config.get('port', 1883)

            self.mqtt_client.connect(broker_host, broker_port, 60)

        except Exception as e:
            logger.error(f"Failed to setup MQTT connection: {e}")

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to building telemetry topics
            topic_pattern = self.config.get('mqtt', {}).get(
                'topic_pattern', 'building/#')
            client.subscribe(topic_pattern)
            logger.info(f"Subscribed to topic pattern: {topic_pattern}")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.info("Disconnected from MQTT broker")

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            # Parse the message
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))

            logger.debug(f"Received message on topic {topic}: {payload}")

            # Write to InfluxDB
            self._write_to_influxdb(topic, payload)

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse JSON payload from topic {topic}: {e}")
        except Exception as e:
            logger.error(f"Error processing message from topic {topic}: {e}")

    def _write_to_influxdb(self, topic: str, payload: Dict[str, Any]) -> None:
        """Write telemetry data to InfluxDB"""
        try:
            if not self.write_api:
                logger.error("InfluxDB write API not available")
                return

            # Extract topic parts for tags
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3:
                building = topic_parts[1] if len(
                    topic_parts) > 1 else 'unknown'
                device = topic_parts[2] if len(topic_parts) > 2 else 'unknown'
            else:
                building = payload.get('building', 'unknown')
                device = payload.get('device', 'unknown')

            # Get timestamp
            timestamp = payload.get('ts')
            if timestamp:
                # Convert from milliseconds to datetime
                dt = datetime.fromtimestamp(timestamp / 1000.0)
            else:
                dt = datetime.utcnow()

            # Get measurement name
            measurement = self.config.get('influxdb', {}).get(
                'measurement', 'telemetry')
            bucket = self.config.get('influxdb', {}).get(
                'bucket', 'building_data')

            # Create points for each telemetry field
            points = []
            points_data = payload.get('points', {})

            for point_name, value in points_data.items():
                if value is not None:
                    point = Point(measurement) \
                        .tag("building", building) \
                        .tag("device", device) \
                        .tag("point", point_name) \
                        .time(dt, WritePrecision.MS)

                    # Handle different data types with separate field names to avoid conflicts
                    if isinstance(value, (int, float)):
                        point = point.field("value", float(value))
                    elif isinstance(value, str):
                        # Different field name for strings
                        point = point.field("text_value", value)
                    elif isinstance(value, bool):
                        # Different field name for booleans
                        point = point.field("bool_value", value)
                    else:
                        # Convert unknown types to string
                        point = point.field("text_value", str(value))

                    points.append(point)

            # Write points to InfluxDB
            if points:
                self.write_api.write(bucket=bucket, record=points)
                logger.debug(
                    f"Written {len(points)} points to InfluxDB for device {device}")

        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")

    def run(self) -> None:
        """Start the collector service"""
        logger.info("Starting telemetry collector")
        self.running = True

        try:
            # Start MQTT loop
            self.mqtt_client.loop_start()

            # Keep the main thread alive
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in collector main loop: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the collector service"""
        logger.info("Stopping telemetry collector")
        self.running = False

        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

        if self.influx_client:
            self.influx_client.close()


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file {config_path} not found, using defaults")
        return {
            'mqtt': {
                'broker': 'localhost',
                'port': 1883,
                'topic_pattern': 'building/#'
            },
            'influxdb': {
                'url': 'http://localhost:8086',
                'token': 'telemetry-token-12345',
                'org': 'telemetry',
                'bucket': 'building_data',
                'measurement': 'telemetry'
            }
        }
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Telemetry Collector (MQTT -> InfluxDB)')
    parser.add_argument('--config', default='collector/config.yaml',
                        help='Path to configuration file')

    args = parser.parse_args()

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load configuration
    config = load_config(args.config)

    # Create and run collector
    collector = TelemetryCollector(config)

    try:
        collector.run()
    except Exception as e:
        logger.error(f"Collector error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

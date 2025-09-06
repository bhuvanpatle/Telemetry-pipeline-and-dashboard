#!/usr/bin/env python3
"""
USAGE EXAMPLE:
python replay/replay_bdg.py --file "Building Data Genome Project 2/electricity_cleaned.csv" --speed 10 --topic-prefix building
python replay/replay_bdg.py --file replay/samples/sample_electricity.csv --speed 1
"""

import argparse
import csv
import json
import logging
import time
import signal
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import paho.mqtt.client as mqtt
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BDGReplay:
    """Building Data Genome Project CSV replay tool"""

    def __init__(self, mqtt_broker: str = 'localhost', mqtt_port: int = 1883):
        self.mqtt_client = None
        self.running = False
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port

        # Initialize MQTT client
        self._setup_mqtt()

    def _setup_mqtt(self) -> None:
        """Setup MQTT client connection"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()

        except Exception as e:
            logger.error(f"Failed to setup MQTT connection: {e}")

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.info("Disconnected from MQTT broker")

    def create_sample_csvs(self, source_dir: str, output_dir: str, num_rows: int = 100) -> None:
        """Create small sample CSV files from BDG data"""
        logger.info(f"Creating sample CSV files in {output_dir}")

        os.makedirs(output_dir, exist_ok=True)

        # List of CSV files to sample
        csv_files = [
            'electricity_cleaned.csv',
            'gas_cleaned.csv',
            'water_cleaned.csv',
            'weather.csv'
        ]

        for csv_file in csv_files:
            source_path = os.path.join(source_dir, csv_file)
            output_path = os.path.join(output_dir, f"sample_{csv_file}")

            if os.path.exists(source_path):
                try:
                    # Read first num_rows of the CSV
                    df = pd.read_csv(source_path, nrows=num_rows)
                    df.to_csv(output_path, index=False)
                    logger.info(
                        f"Created sample file: {output_path} ({len(df)} rows)")
                except Exception as e:
                    logger.error(
                        f"Failed to create sample for {csv_file}: {e}")
            else:
                logger.warning(f"Source file not found: {source_path}")

    def parse_csv_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse CSV data and convert to telemetry format"""
        logger.info(f"Parsing CSV file: {file_path}")

        data_points = []

        try:
            df = pd.read_csv(file_path)

            # Handle different CSV formats
            if 'timestamp' in df.columns:
                timestamp_col = 'timestamp'
            elif 'ts' in df.columns:
                timestamp_col = 'ts'
            else:
                logger.error("No timestamp column found in CSV")
                return []

            # Convert timestamp to datetime
            df[timestamp_col] = pd.to_datetime(df[timestamp_col])

            # Determine file type from filename
            filename = os.path.basename(file_path).lower()
            if 'electricity' in filename:
                meter_type = 'electricity'
            elif 'gas' in filename:
                meter_type = 'gas'
            elif 'water' in filename:
                meter_type = 'water'
            elif 'weather' in filename:
                meter_type = 'weather'
            else:
                meter_type = 'unknown'

            # Process each row
            for _, row in df.iterrows():
                timestamp = row[timestamp_col]
                ts_ms = int(timestamp.timestamp() * 1000)

                # Extract building/device columns (skip timestamp)
                points = {}
                for col in df.columns:
                    if col != timestamp_col and pd.notna(row[col]):
                        points[col] = float(row[col]) if isinstance(
                            row[col], (int, float)) else str(row[col])

                # Create telemetry payload for each building/meter
                if meter_type == 'weather':
                    # Weather data - single device
                    data_point = {
                        "ts": ts_ms,
                        "device": "weather_station",
                        "building": row.get('site_id', 'unknown_site'),
                        "points": {k: v for k, v in points.items() if k != 'site_id'}
                    }
                    data_points.append(data_point)
                else:
                    # Energy meter data - multiple buildings/meters per row
                    for col, value in points.items():
                        if pd.notna(value) and col != 'site_id':
                            building_device = col.split('_', 2)
                            if len(building_device) >= 3:
                                building = building_device[0]
                                device_type = building_device[1]
                                device_name = building_device[2]
                                device_id = f"{building}_{device_type}_{device_name}"

                                data_point = {
                                    "ts": ts_ms,
                                    "device": device_id,
                                    "building": building,
                                    "points": {
                                        meter_type: value,
                                        "meter_type": meter_type
                                    }
                                }
                                data_points.append(data_point)

        except Exception as e:
            logger.error(f"Error parsing CSV file: {e}")

        logger.info(f"Parsed {len(data_points)} data points")
        return data_points

    def replay_data(self, data_points: List[Dict[str, Any]], speed: float = 1.0,
                    topic_prefix: str = "building") -> None:
        """Replay data points to MQTT with time acceleration"""
        if not data_points:
            logger.error("No data points to replay")
            return

        logger.info(
            f"Starting replay of {len(data_points)} points with {speed}x speed")
        self.running = True

        # Sort data points by timestamp
        data_points.sort(key=lambda x: x['ts'])

        start_time = time.time()
        first_timestamp = data_points[0]['ts'] / 1000.0  # Convert to seconds

        for i, data_point in enumerate(data_points):
            if not self.running:
                break

            try:
                # Calculate timing
                data_timestamp = data_point['ts'] / 1000.0
                elapsed_data_time = data_timestamp - first_timestamp
                target_elapsed_time = elapsed_data_time / speed
                actual_elapsed_time = time.time() - start_time

                # Wait if we're ahead of schedule
                sleep_time = target_elapsed_time - actual_elapsed_time
                if sleep_time > 0:
                    time.sleep(sleep_time)

                # Create MQTT topic
                building = data_point.get('building', 'unknown')
                device = data_point.get('device', 'unknown')
                topic = f"{topic_prefix}/{building}/{device}/telemetry"

                # Publish to MQTT
                if self.mqtt_client and self.mqtt_client.is_connected():
                    payload = json.dumps(data_point)
                    self.mqtt_client.publish(topic, payload)

                    if i % 100 == 0:  # Log progress every 100 points
                        logger.info(
                            f"Replayed {i+1}/{len(data_points)} points")
                else:
                    logger.warning("MQTT client not connected")

            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error replaying data point {i}: {e}")

        logger.info("Replay completed")
        self.stop()

    def stop(self) -> None:
        """Stop the replay"""
        logger.info("Stopping BDG replay")
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Building Data Genome CSV Replay Tool')
    parser.add_argument('--file', required=True,
                        help='Path to CSV file to replay')
    parser.add_argument('--speed', type=float, default=1.0,
                        help='Playback speed multiplier (1.0 = real time, 10.0 = 10x faster)')
    parser.add_argument('--topic-prefix', default='building',
                        help='MQTT topic prefix')
    parser.add_argument('--broker', default='localhost',
                        help='MQTT broker hostname')
    parser.add_argument('--port', type=int, default=1883,
                        help='MQTT broker port')
    parser.add_argument('--create-samples', action='store_true',
                        help='Create sample CSV files from BDG data')
    parser.add_argument('--sample-rows', type=int, default=100,
                        help='Number of rows for sample files')

    args = parser.parse_args()

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create replay instance
    replay = BDGReplay(mqtt_broker=args.broker, mqtt_port=args.port)

    try:
        if args.create_samples:
            # Create sample CSV files
            source_dir = "Building Data Genome Project 2"
            output_dir = "replay/samples"
            replay.create_sample_csvs(source_dir, output_dir, args.sample_rows)
        else:
            # Parse and replay data
            data_points = replay.parse_csv_data(args.file)
            if data_points:
                replay.replay_data(data_points, args.speed, args.topic_prefix)
            else:
                logger.error("No data points found to replay")

    except Exception as e:
        logger.error(f"Replay error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

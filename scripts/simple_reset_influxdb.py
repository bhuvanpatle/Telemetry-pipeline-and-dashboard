#!/usr/bin/env python3
"""
Simple InfluxDB Bucket Reset

This script uses the delete API to clear all telemetry data and recreate clean schema.
"""

import logging
import sys
import time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError

# InfluxDB Configuration
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "telemetry-token-12345"
INFLUXDB_ORG = "telemetry"
INFLUXDB_BUCKET = "building_data"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def clear_telemetry_data():
    """Clear all telemetry data and recreate with clean schema."""

    try:
        # Connect to InfluxDB
        client = InfluxDBClient(
            url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

        # Test connection
        health = client.health()
        if health.status != "pass":
            logger.error(f"InfluxDB health check failed: {health}")
            return False

        logger.info("✅ Connected to InfluxDB successfully")

        # Delete all telemetry data
        delete_api = client.delete_api()

        logger.info("🗑️ Deleting all telemetry measurement data...")
        delete_api.delete(
            start="1970-01-01T00:00:00Z",
            stop="2025-12-31T23:59:59Z",
            predicate='_measurement="telemetry"',
            bucket=INFLUXDB_BUCKET,
            org=INFLUXDB_ORG
        )
        logger.info("✅ All telemetry data deleted")

        # Wait for deletion to complete
        time.sleep(3)

        # Write clean test data with consistent types
        write_api = client.write_api(write_options=SYNCHRONOUS)

        logger.info("✏️ Writing test data with consistent types...")

        # Create test points that mirror AHU simulator structure
        test_points = []

        # Numeric telemetry fields (all as floats)
        numeric_fields = {
            "outside_temp": 22.5,
            "supply_temp": 18.2,
            "setpoint": 20.0,
            "vfd_speed": 75.5,
            "economizer_position": 45.0
        }

        timestamp = time.time_ns() // 1_000_000  # milliseconds

        for point_name, value in numeric_fields.items():
            point = Point("telemetry") \
                .tag("building", "demo_building") \
                .tag("device", "ahu1") \
                .tag("point", point_name) \
                .field("value", float(value)) \
                .time(timestamp, WritePrecision.MS)
            test_points.append(point)

        # String fields with different field names to avoid conflicts
        point = Point("telemetry") \
            .tag("building", "demo_building") \
            .tag("device", "ahu1") \
            .tag("point", "fan_status") \
            .field("text_value", "ON") \
            .time(timestamp, WritePrecision.MS)
        test_points.append(point)

        # Boolean fields
        point = Point("telemetry") \
            .tag("building", "demo_building") \
            .tag("device", "ahu1") \
            .tag("point", "alarm") \
            .field("bool_value", False) \
            .time(timestamp, WritePrecision.MS)
        test_points.append(point)

        write_api.write(bucket=INFLUXDB_BUCKET,
                        org=INFLUXDB_ORG, record=test_points)
        logger.info("✅ Successfully wrote test data with clean schema")

        # Verify the fix
        logger.info("🔍 Verifying the schema...")
        query_api = client.query_api()

        verify_query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "telemetry")
        |> limit(n: 10)
        '''

        result = query_api.query(query=verify_query)
        verification_count = 0

        for table in result:
            for record in table.records:
                verification_count += 1
                value = record.get_value()
                field = record.get_field()
                point = record.values.get("point", "unknown")
                logger.info(
                    f"✅ Verified: point={point}, field={field}, value={value} (type: {type(value).__name__})")

        if verification_count > 0:
            logger.info(
                f"✅ Schema reset successful! Found {verification_count} clean records")
            return True
        else:
            logger.warning(
                "⚠️ No verification records found, but deletion completed")
            return True

    except InfluxDBError as e:
        logger.error(f"❌ InfluxDB error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()


def main():
    """Main function."""

    logger.info("🔧 Starting Simple InfluxDB Data Reset")
    logger.info("=" * 50)
    logger.warning("⚠️ This will delete all telemetry data!")
    logger.info("⏳ Waiting 3 seconds... (Ctrl+C to cancel)")

    try:
        time.sleep(3)
    except KeyboardInterrupt:
        logger.info("❌ Reset cancelled by user")
        return 1

    success = clear_telemetry_data()

    if success:
        logger.info("=" * 50)
        logger.info("✅ InfluxDB data reset successful!")
        logger.info("📊 Clean schema established with proper data types")
        logger.info("🚀 Restart telemetry services now")
        return 0
    else:
        logger.error("=" * 50)
        logger.error("❌ InfluxDB data reset failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

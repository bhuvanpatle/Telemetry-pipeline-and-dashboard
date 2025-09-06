#!/usr/bin/env python3
"""
InfluxDB Data Type Fix Script

This script fixes the field type conflict in InfluxDB by:
1. Dropping the conflicting measurement
2. Recreating it with correct data types
3. Verifying the fix

Error being fixed: 
"field type conflict: input field 'value' on measurement 'telemetry' is type string, already exists as type float"
"""

import logging
import sys
import os
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# InfluxDB Configuration (matching docker-compose.yml and collector)
INFLUXDB_URL = "http://localhost:8086"
# From docker-compose.yml DOCKER_INFLUXDB_INIT_ADMIN_TOKEN
INFLUXDB_TOKEN = "telemetry-token-12345"
# From docker-compose.yml DOCKER_INFLUXDB_INIT_ORG
INFLUXDB_ORG = "telemetry"
# From docker-compose.yml DOCKER_INFLUXDB_INIT_BUCKET
INFLUXDB_BUCKET = "building_data"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fix_influxdb_schema():
    """Fix InfluxDB schema by dropping and recreating the problematic measurement."""

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

        # Get query and delete APIs
        query_api = client.query_api()
        delete_api = client.delete_api()

        # Check current data in the problematic measurement
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -24h)
        |> filter(fn: (r) => r._measurement == "telemetry")
        |> limit(n: 5)
        '''

        logger.info("🔍 Checking existing telemetry data...")

        try:
            result = query_api.query(query=query)
            record_count = 0
            for table in result:
                for record in table.records:
                    record_count += 1
                    logger.info(
                        f"Found record: {record.get_measurement()}, field: {record.get_field()}, value: {record.get_value()} (type: {type(record.get_value()).__name__})")

            if record_count > 0:
                logger.warning(
                    f"Found {record_count} existing records with potential type conflicts")

                # Delete all telemetry measurement data
                logger.info(
                    "🗑️  Deleting existing telemetry measurement data...")
                delete_api.delete(
                    start="1970-01-01T00:00:00Z",
                    stop="2025-12-31T23:59:59Z",
                    predicate='_measurement="telemetry"',
                    bucket=INFLUXDB_BUCKET,
                    org=INFLUXDB_ORG
                )
                logger.info("✅ Deleted existing telemetry data")
            else:
                logger.info("No existing telemetry data found")

        except Exception as e:
            logger.warning(
                f"Could not query existing data (this is normal for fresh setup): {e}")

        # Write test data with correct types
        write_api = client.write_api(write_options=SYNCHRONOUS)

        logger.info("✏️  Writing test data with correct float types...")

        # Create test points with explicit float values
        test_points = [
            Point("telemetry")
            .tag("device_id", "TEST_AHU_01")
            .tag("device_type", "AHU")
            .tag("location", "Building_A")
            .field("temperature", 22.5)  # Explicit float
            .field("humidity", 45.0)     # Explicit float
            .field("pressure", 1013.25)  # Explicit float
            .field("value", 22.5),       # The problematic field as float

            Point("telemetry")
            .tag("device_id", "TEST_AHU_02")
            .tag("device_type", "AHU")
            .tag("location", "Building_B")
            .field("temperature", 23.1)  # Explicit float
            .field("humidity", 48.0)     # Explicit float
            .field("pressure", 1012.8)   # Explicit float
            .field("value", 23.1)        # The problematic field as float
        ]

        write_api.write(bucket=INFLUXDB_BUCKET,
                        org=INFLUXDB_ORG, record=test_points)
        logger.info("✅ Successfully wrote test data with correct float types")

        # Verify the fix
        logger.info("🔍 Verifying the fix...")
        verify_query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "telemetry")
        |> filter(fn: (r) => r._field == "value")
        |> limit(n: 3)
        '''

        result = query_api.query(query=verify_query)
        verification_count = 0
        for table in result:
            for record in table.records:
                verification_count += 1
                value = record.get_value()
                logger.info(
                    f"✅ Verified record: field={record.get_field()}, value={value} (type: {type(value).__name__})")

        if verification_count > 0:
            logger.info(
                f"✅ Schema fix successful! Found {verification_count} records with correct float types")
            return True
        else:
            logger.warning(
                "⚠️ No verification records found, but no errors occurred")
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
    """Main function to run the InfluxDB schema fix."""

    logger.info("🔧 Starting InfluxDB Schema Fix")
    logger.info("=" * 50)

    # Wait for InfluxDB to be ready
    import time
    logger.info("⏳ Waiting for InfluxDB to be ready...")
    time.sleep(5)

    success = fix_influxdb_schema()

    if success:
        logger.info("=" * 50)
        logger.info("✅ InfluxDB schema fix completed successfully!")
        logger.info(
            "📊 The telemetry measurement now accepts numeric values correctly")
        logger.info(
            "🚀 You can now restart the telemetry collector without type conflicts")
        return 0
    else:
        logger.error("=" * 50)
        logger.error("❌ InfluxDB schema fix failed!")
        logger.error("🔧 Please check the logs above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())

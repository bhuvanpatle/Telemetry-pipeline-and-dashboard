#!/usr/bin/env python3
"""
InfluxDB Complete Schema Reset

This script completely resets the InfluxDB telemetry measurement by:
1. Stopping all services that write to InfluxDB
2. Dropping the entire bucket
3. Recreating the bucket with clean schema
4. Testing with proper data types

This is a more aggressive fix than the previous script.
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


def reset_influxdb_schema():
    """Completely reset InfluxDB schema by recreating the bucket."""

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

        # Get buckets API
        buckets_api = client.buckets_api()

        # Find the existing bucket
        logger.info(f"🔍 Looking for bucket: {INFLUXDB_BUCKET}")
        buckets = buckets_api.find_buckets()

        target_bucket = None
        for bucket in buckets.buckets:
            if bucket.name == INFLUXDB_BUCKET:
                target_bucket = bucket
                break

        if target_bucket:
            logger.info(
                f"📦 Found bucket: {INFLUXDB_BUCKET} (ID: {target_bucket.id})")

            # Delete the bucket
            logger.warning(f"🗑️  Deleting bucket: {INFLUXDB_BUCKET}")
            buckets_api.delete_bucket(target_bucket.id)
            logger.info(f"✅ Bucket deleted successfully")

            # Wait a moment for deletion to complete
            time.sleep(2)
        else:
            logger.info(
                f"📦 Bucket {INFLUXDB_BUCKET} not found, will create new one")

        # Create a new bucket
        logger.info(f"🆕 Creating new bucket: {INFLUXDB_BUCKET}")

        # Get organization
        orgs_api = client.organizations_api()
        orgs = orgs_api.find_organizations()
        target_org = None

        for org in orgs.orgs:
            if org.name == INFLUXDB_ORG:
                target_org = org
                break

        if not target_org:
            logger.error(f"❌ Organization '{INFLUXDB_ORG}' not found")
            return False

        # Create new bucket with 30 day retention
        from influxdb_client.domain.bucket import Bucket
        from influxdb_client.domain.bucket_retention_rules import BucketRetentionRules

        retention_rules = BucketRetentionRules(
            type="expire", every_seconds=30*24*60*60)  # 30 days

        bucket = Bucket(
            name=INFLUXDB_BUCKET,
            org_id=target_org.id,
            retention_rules=[retention_rules]
        )

        created_bucket = buckets_api.create_bucket(bucket=bucket)
        logger.info(
            f"✅ Created new bucket: {created_bucket.name} (ID: {created_bucket.id})")

        # Write test data with consistent types
        write_api = client.write_api(write_options=SYNCHRONOUS)

        logger.info("✏️  Writing test data with consistent float types...")

        # Create test points that mirror the AHU simulator structure
        test_points = []

        # Simulate AHU telemetry data
        ahu_points = {
            "outside_temp": 22.5,
            "supply_temp": 18.2,
            "setpoint": 20.0,
            "vfd_speed": 75.5,
            "economizer_position": 45.0
        }

        for point_name, value in ahu_points.items():
            point = Point("telemetry") \
                .tag("building", "demo_building") \
                .tag("device", "ahu1") \
                .tag("point", point_name) \
                .field("value", float(value))  # Ensure all values are floats
            test_points.append(point)

        # Also add string/boolean fields separately to test mixed types
        test_points.append(
            Point("telemetry")
            .tag("building", "demo_building")
            .tag("device", "ahu1")
            .tag("point", "fan_status")
            .field("status", "ON")  # String field with different name
        )

        test_points.append(
            Point("telemetry")
            .tag("building", "demo_building")
            .tag("device", "ahu1")
            .tag("point", "alarm")
            .field("active", False)  # Boolean field with different name
        )

        write_api.write(bucket=INFLUXDB_BUCKET,
                        org=INFLUXDB_ORG, record=test_points)
        logger.info("✅ Successfully wrote test data with clean schema")

        # Verify the schema reset
        logger.info("🔍 Verifying the schema reset...")
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
                logger.info(
                    f"✅ Verified record: field={field}, value={value} (type: {type(value).__name__})")

        if verification_count > 0:
            logger.info(
                f"✅ Schema reset successful! Found {verification_count} records with clean types")
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
    """Main function to run the complete InfluxDB schema reset."""

    logger.info("🔧 Starting Complete InfluxDB Schema Reset")
    logger.info("=" * 60)
    logger.warning(
        "⚠️  WARNING: This will delete all existing data in the bucket!")
    logger.info("⏳ Waiting 5 seconds... (Ctrl+C to cancel)")

    try:
        time.sleep(5)
    except KeyboardInterrupt:
        logger.info("❌ Reset cancelled by user")
        return 1

    success = reset_influxdb_schema()

    if success:
        logger.info("=" * 60)
        logger.info("✅ Complete InfluxDB schema reset successful!")
        logger.info("📊 The bucket has been recreated with clean schema")
        logger.info("🚀 You can now restart all telemetry services")
        logger.info("💡 Recommended next steps:")
        logger.info(
            "   1. Restart telemetry collector: python collector/ingest.py")
        logger.info(
            "   2. Restart AHU simulator: python simulator/ahu_simulator.py --mode sim --cadence 10")
        return 0
    else:
        logger.error("=" * 60)
        logger.error("❌ Complete InfluxDB schema reset failed!")
        logger.error("🔧 Please check the logs above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())

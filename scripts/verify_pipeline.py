#!/usr/bin/env python3
"""
Comprehensive Telemetry Pipeline Verification Script

This script systematically checks all components of the telemetry pipeline:
1. Docker services (InfluxDB, Mosquitto, Grafana)
2. Network connectivity
3. API endpoints  
4. Data flow from MQTT to InfluxDB
5. Frontend accessibility
6. Grafana dashboards

Usage: python scripts/verify_pipeline.py
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import aiohttp
import paho.mqtt.client as mqtt
import requests
from influxdb_client import InfluxDBClient

# Configuration
DOCKER_SERVICES = ['mosquitto', 'influxdb', 'grafana']
MQTT_BROKER = 'localhost'
MQTT_PORT = 1883
INFLUXDB_URL = 'http://localhost:8086'
INFLUXDB_TOKEN = 'telemetry-token-12345'
INFLUXDB_ORG = 'telemetry'
INFLUXDB_BUCKET = 'building_data'
GRAFANA_URL = 'http://localhost:3000'
API_URL = 'http://localhost:8000'
FRONTEND_URL = 'http://localhost:3001'

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TelemetryVerifier:
    """Comprehensive telemetry pipeline verification"""

    def __init__(self):
        self.verification_results = {
            'docker_services': {},
            'network_connectivity': {},
            'influxdb_connection': False,
            'mqtt_connection': False,
            'api_endpoints': {},
            'grafana_access': False,
            'frontend_access': False,
            'data_flow': False,
            'overall_health': False
        }

    async def verify_all(self) -> Dict:
        """Run all verification checks"""
        logger.info("🔍 TELEMETRY PIPELINE COMPREHENSIVE VERIFICATION")
        logger.info("=" * 60)

        # Step 1: Docker Services
        await self.check_docker_services()

        # Step 2: Network Connectivity
        await self.check_network_connectivity()

        # Step 3: InfluxDB Connection
        await self.check_influxdb()

        # Step 4: MQTT Connection
        await self.check_mqtt()

        # Step 5: API Endpoints
        await self.check_api_endpoints()

        # Step 6: Grafana Access
        await self.check_grafana()

        # Step 7: Frontend Access
        await self.check_frontend()

        # Step 8: End-to-End Data Flow
        await self.test_data_flow()

        # Step 9: Overall Assessment
        self.assess_overall_health()

        # Step 10: Generate Report
        self.generate_report()

        return self.verification_results

    async def check_docker_services(self):
        """Check Docker service status"""
        logger.info("\\n1️⃣ Checking Docker Services...")

        try:
            result = subprocess.run(['docker-compose', 'ps'],
                                    capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.info("✅ Docker Compose is accessible")

                for service in DOCKER_SERVICES:
                    service_check = subprocess.run(
                        ['docker', 'ps', '--filter',
                            f'name={service}', '--format', 'table {{.Names}}\\t{{.Status}}'],
                        capture_output=True, text=True, timeout=10
                    )

                    if service in service_check.stdout and 'Up' in service_check.stdout:
                        self.verification_results['docker_services'][service] = True
                        logger.info(f"  ✅ {service}: Running")
                    else:
                        self.verification_results['docker_services'][service] = False
                        logger.warning(f"  ❌ {service}: Not running")
            else:
                logger.error("❌ Docker Compose not accessible")

        except Exception as e:
            logger.error(f"❌ Docker check failed: {e}")

    async def check_network_connectivity(self):
        """Check network connectivity to all services"""
        logger.info("\\n2️⃣ Checking Network Connectivity...")

        endpoints = {
            'InfluxDB': (INFLUXDB_URL, 8086),
            'Mosquitto': (MQTT_BROKER, MQTT_PORT),
            'Grafana': (GRAFANA_URL, 3000)
        }

        for name, (host, port) in endpoints.items():
            try:
                if name == 'Mosquitto':
                    # Test MQTT port specifically
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((MQTT_BROKER, MQTT_PORT))
                    sock.close()

                    if result == 0:
                        self.verification_results['network_connectivity'][name] = True
                        logger.info(f"  ✅ {name}: Port {port} accessible")
                    else:
                        self.verification_results['network_connectivity'][name] = False
                        logger.warning(
                            f"  ❌ {name}: Port {port} not accessible")
                else:
                    # Test HTTP endpoints
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                        url = host.replace('localhost', '127.0.0.1')
                        async with session.get(url) as response:
                            if response.status < 500:
                                self.verification_results['network_connectivity'][name] = True
                                logger.info(
                                    f"  ✅ {name}: HTTP accessible (status: {response.status})")
                            else:
                                self.verification_results['network_connectivity'][name] = False
                                logger.warning(
                                    f"  ❌ {name}: HTTP error (status: {response.status})")

            except Exception as e:
                self.verification_results['network_connectivity'][name] = False
                logger.warning(f"  ❌ {name}: Connection failed - {e}")

    async def check_influxdb(self):
        """Check InfluxDB connection and data"""
        logger.info("\\n3️⃣ Checking InfluxDB...")

        try:
            client = InfluxDBClient(
                url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

            # Health check
            health = client.health()
            if health.status == "pass":
                logger.info("  ✅ InfluxDB: Health check passed")

                # Check for data
                query_api = client.query_api()
                query = f'''
                from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "telemetry")
                |> limit(n: 5)
                '''

                result = query_api.query(query=query)
                record_count = sum(len(table.records) for table in result)

                if record_count > 0:
                    logger.info(
                        f"  ✅ InfluxDB: Found {record_count} telemetry records")
                else:
                    logger.info(
                        "  ⚠️  InfluxDB: No telemetry data found (may be expected if just started)")

                self.verification_results['influxdb_connection'] = True
            else:
                logger.error(f"  ❌ InfluxDB: Health check failed - {health}")

            client.close()

        except Exception as e:
            logger.error(f"  ❌ InfluxDB: Connection failed - {e}")

    async def check_mqtt(self):
        """Check MQTT broker connection"""
        logger.info("\\n4️⃣ Checking MQTT Broker...")

        try:
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    logger.info("  ✅ MQTT: Successfully connected to broker")
                    self.verification_results['mqtt_connection'] = True
                else:
                    logger.error(f"  ❌ MQTT: Connection failed with code {rc}")

            client = mqtt.Client()
            client.on_connect = on_connect
            client.connect(MQTT_BROKER, MQTT_PORT, 10)
            client.loop_start()

            # Wait for connection
            time.sleep(2)
            client.loop_stop()
            client.disconnect()

        except Exception as e:
            logger.error(f"  ❌ MQTT: Connection failed - {e}")

    async def check_api_endpoints(self):
        """Check API endpoints"""
        logger.info("\\n5️⃣ Checking API Endpoints...")

        endpoints = {
            'health': f'{API_URL}/health',
            'last_telemetry': f'{API_URL}/last?topic=building/ahu1/telemetry',
            'stats': f'{API_URL}/stats'
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for name, url in endpoints.items():
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.verification_results['api_endpoints'][name] = True
                            logger.info(
                                f"  ✅ API {name}: Accessible (status: {response.status})")
                        else:
                            self.verification_results['api_endpoints'][name] = False
                            logger.warning(
                                f"  ❌ API {name}: Error (status: {response.status})")

                except Exception as e:
                    self.verification_results['api_endpoints'][name] = False
                    logger.warning(f"  ❌ API {name}: Connection failed - {e}")

    async def check_grafana(self):
        """Check Grafana access"""
        logger.info("\\n6️⃣ Checking Grafana...")

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(GRAFANA_URL) as response:
                    if response.status == 200:
                        self.verification_results['grafana_access'] = True
                        logger.info("  ✅ Grafana: Accessible")
                        logger.info(f"  📊 Grafana Dashboard: {GRAFANA_URL}")
                    else:
                        logger.warning(
                            f"  ❌ Grafana: Error (status: {response.status})")

        except Exception as e:
            logger.warning(f"  ❌ Grafana: Connection failed - {e}")

    async def check_frontend(self):
        """Check frontend access"""
        logger.info("\\n7️⃣ Checking Frontend...")

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(FRONTEND_URL) as response:
                    if response.status == 200:
                        self.verification_results['frontend_access'] = True
                        logger.info("  ✅ Frontend: Accessible")
                        logger.info(f"  🌐 React Dashboard: {FRONTEND_URL}")
                    else:
                        logger.warning(
                            f"  ❌ Frontend: Error (status: {response.status})")

        except Exception as e:
            logger.warning(f"  ❌ Frontend: Not running - {e}")
            logger.info("  💡 To start frontend: cd frontend && npm start")

    async def test_data_flow(self):
        """Test end-to-end data flow"""
        logger.info("\\n8️⃣ Testing End-to-End Data Flow...")

        if not self.verification_results['mqtt_connection']:
            logger.warning(
                "  ⚠️  Skipping data flow test - MQTT not connected")
            return

        try:
            # Publish test message to MQTT
            test_payload = {
                "timestamp": datetime.now().isoformat(),
                "device_id": "TEST_VERIFICATION_AHU",
                "temperature": 25.5,
                "humidity": 50.0,
                "pressure": 1013.25,
                "value": 25.5  # This was the problematic field
            }

            client = mqtt.Client()
            client.connect(MQTT_BROKER, MQTT_PORT, 10)

            topic = "building/test_verification/telemetry"
            client.publish(topic, json.dumps(test_payload))
            logger.info("  📤 Published test telemetry message")

            client.disconnect()

            # Wait a bit for processing
            await asyncio.sleep(5)

            # Check if data appeared in InfluxDB
            if self.verification_results['influxdb_connection']:
                try:
                    client = InfluxDBClient(
                        url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
                    query_api = client.query_api()

                    query = f'''
                    from(bucket: "{INFLUXDB_BUCKET}")
                    |> range(start: -1h)
                    |> filter(fn: (r) => r._measurement == "telemetry")
                    |> filter(fn: (r) => r.device_id == "TEST_VERIFICATION_AHU")
                    '''

                    result = query_api.query(query=query)
                    record_count = sum(len(table.records) for table in result)

                    if record_count > 0:
                        self.verification_results['data_flow'] = True
                        logger.info(
                            f"  ✅ Data Flow: Test message found in InfluxDB ({record_count} records)")
                    else:
                        logger.warning(
                            "  ⚠️  Data Flow: Test message not found in InfluxDB")

                    client.close()

                except Exception as e:
                    logger.warning(
                        f"  ⚠️  Data Flow: Could not verify in InfluxDB - {e}")

        except Exception as e:
            logger.error(f"  ❌ Data Flow: Test failed - {e}")

    def assess_overall_health(self):
        """Assess overall system health"""
        logger.info("\\n9️⃣ Overall Health Assessment...")

        # Count successful checks
        docker_ok = sum(self.verification_results['docker_services'].values())
        network_ok = sum(
            self.verification_results['network_connectivity'].values())
        api_ok = sum(self.verification_results['api_endpoints'].values())

        total_checks = (
            len(self.verification_results['docker_services']) +
            len(self.verification_results['network_connectivity']) +
            len(self.verification_results['api_endpoints']) +
            3  # influxdb, mqtt, grafana individual checks
        )

        successful_checks = (
            docker_ok + network_ok + api_ok +
            (1 if self.verification_results['influxdb_connection'] else 0) +
            (1 if self.verification_results['mqtt_connection'] else 0) +
            (1 if self.verification_results['grafana_access'] else 0)
        )

        health_percentage = (successful_checks / total_checks) * \
            100 if total_checks > 0 else 0

        self.verification_results['overall_health'] = health_percentage

        if health_percentage >= 90:
            logger.info(
                f"  ✅ System Health: EXCELLENT ({health_percentage:.1f}%)")
        elif health_percentage >= 75:
            logger.info(
                f"  ⚠️  System Health: GOOD ({health_percentage:.1f}%)")
        elif health_percentage >= 50:
            logger.warning(
                f"  ⚠️  System Health: FAIR ({health_percentage:.1f}%)")
        else:
            logger.error(f"  ❌ System Health: POOR ({health_percentage:.1f}%)")

    def generate_report(self):
        """Generate comprehensive verification report"""
        logger.info("\\n🔟 Verification Report")
        logger.info("=" * 60)

        # Core Services Status
        logger.info("\\n📋 CORE SERVICES STATUS:")
        for service, status in self.verification_results['docker_services'].items():
            status_icon = "✅" if status else "❌"
            logger.info(
                f"  {status_icon} {service.capitalize()}: {'Running' if status else 'Not Running'}")

        # Connectivity Status
        logger.info("\\n🌐 CONNECTIVITY STATUS:")
        for service, status in self.verification_results['network_connectivity'].items():
            status_icon = "✅" if status else "❌"
            logger.info(
                f"  {status_icon} {service}: {'Accessible' if status else 'Not Accessible'}")

        # API Status
        logger.info("\\n🔌 API ENDPOINTS STATUS:")
        for endpoint, status in self.verification_results['api_endpoints'].items():
            status_icon = "✅" if status else "❌"
            logger.info(
                f"  {status_icon} {endpoint}: {'Working' if status else 'Not Working'}")

        # Data Flow
        logger.info("\\n📊 DATA FLOW:")
        data_flow_icon = "✅" if self.verification_results['data_flow'] else "❌"
        logger.info(
            f"  {data_flow_icon} End-to-End: {'Working' if self.verification_results['data_flow'] else 'Not Working'}")

        # Access URLs
        logger.info("\\n🌐 ACCESS URLS:")
        logger.info(f"  📊 Grafana Dashboard: {GRAFANA_URL}")
        logger.info(f"  🔌 API Status: {API_URL}/health")
        if self.verification_results['frontend_access']:
            logger.info(f"  🌐 React Frontend: {FRONTEND_URL}")
        else:
            logger.info(
                "  💡 React Frontend: Not running (cd frontend && npm start)")

        # Next Steps
        logger.info("\\n🚀 NEXT STEPS:")
        if self.verification_results['overall_health'] >= 90:
            logger.info("  🎉 System is running optimally!")
            logger.info(
                "  📈 Start the AHU simulator: python simulator/ahu_simulator.py")
            logger.info("  📊 View real-time data in Grafana dashboards")
        else:
            logger.info("  🔧 Issues found. Recommended actions:")

            if not all(self.verification_results['docker_services'].values()):
                logger.info(
                    "    • Start missing Docker services: docker-compose up -d")

            if not self.verification_results['frontend_access']:
                logger.info(
                    "    • Start React frontend: cd frontend && npm start")

            if not self.verification_results['data_flow']:
                logger.info(
                    "    • Check telemetry collector: python collector/ingest.py")

        logger.info("\\n" + "=" * 60)
        logger.info(
            f"🏁 VERIFICATION COMPLETE - System Health: {self.verification_results['overall_health']:.1f}%")


async def main():
    """Main verification function"""
    verifier = TelemetryVerifier()
    results = await verifier.verify_all()
    return results

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\\n⏹️  Verification interrupted by user")
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        sys.exit(1)

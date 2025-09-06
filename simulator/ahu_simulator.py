#!/usr/bin/env python3
"""
USAGE EXAMPLE:
python simulator/ahu_simulator.py --mode sim --cadence 2 --config simulator/config.yaml
python simulator/ahu_simulator.py --mode live --cadence 5
"""

import argparse
import json
import logging
import time
import signal
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass
import threading
import yaml
import requests
import paho.mqtt.client as mqtt
from datetime import datetime
import random
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AHUState:
    """Air Handling Unit state variables"""
    supply_temp: float = 18.0
    outside_temp: float = 25.0
    setpoint: float = 18.0
    vfd_speed: float = 50.0
    fan_status: str = "ON"
    alarm: Optional[str] = None
    economizer_position: float = 0.0


class PIDController:
    """Simple PID controller for temperature control"""

    def __init__(self, kp: float = 1.0, ki: float = 0.1, kd: float = 0.05):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.prev_error = 0.0
        self.integral = 0.0

    def update(self, error: float, dt: float) -> float:
        """Update PID controller and return control output"""
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return output


class AHUSimulator:
    """Air Handling Unit Simulator with DDC logic"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state = AHUState()
        self.pid = PIDController(
            kp=config.get('pid_kp', 2.0),
            ki=config.get('pid_ki', 0.1),
            kd=config.get('pid_kd', 0.05)
        )
        self.running = False
        self.mqtt_client = None
        self.last_update = time.time()

        # Initialize MQTT client
        self._setup_mqtt()

    def _setup_mqtt(self) -> None:
        """Setup MQTT client connection"""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

        broker_host = self.config.get('mqtt_broker', 'localhost')
        broker_port = self.config.get('mqtt_port', 1883)

        try:
            self.mqtt_client.connect(broker_host, broker_port, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.info("Disconnected from MQTT broker")

    def get_outside_temp(self, mode: str) -> float:
        """Get outside temperature from API or simulation"""
        if mode == 'live':
            try:
                # Use Open-Meteo API for real weather data
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    'latitude': self.config.get('latitude', 40.7128),
                    'longitude': self.config.get('longitude', -74.0060),
                    'current_weather': 'true',
                    'temperature_unit': 'celsius'
                }
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return data['current_weather']['temperature']
            except Exception as e:
                logger.warning(
                    f"Failed to get weather data: {e}, using simulation")

        # Fallback to simulation
        now = datetime.now()
        hour = now.hour
        # Simulate daily temperature variation
        base_temp = 20.0 + 10.0 * math.sin((hour - 6) * math.pi / 12)
        noise = random.uniform(-2.0, 2.0)
        return base_temp + noise

    def update_control_logic(self, dt: float) -> None:
        """Update DDC control logic"""
        # Temperature control with PID (error = actual - setpoint for cooling control)
        temp_error = self.state.supply_temp - self.state.setpoint
        pid_output = self.pid.update(temp_error, dt)

        # Update VFD speed based on PID output (0-100% range)
        # When supply temp is below setpoint (cooling not needed), reduce speed
        if temp_error < -2.0:  # Much colder than needed
            self.state.vfd_speed = max(
                0.0, min(100.0, 20.0 + pid_output * 5.0))
        else:  # Normal or warm
            self.state.vfd_speed = max(
                0.0, min(100.0, 50.0 + pid_output * 10.0))

        # Economizer logic based on outside temperature
        if self.state.outside_temp < self.state.setpoint + 2.0:
            # Use free cooling when outside temp is favorable
            self.state.economizer_position = min(100.0,
                                                 (self.state.setpoint + 2.0 - self.state.outside_temp) * 25.0)
        else:
            self.state.economizer_position = 0.0

        # Simulate supply air temperature response with more effective cooling
        cooling_effect = (self.state.vfd_speed - 50.0) / \
            50.0 * 1.5  # More cooling effect
        economizer_effect = self.state.economizer_position / 100.0 * \
            (self.state.outside_temp - self.state.supply_temp) * 0.1

        temp_change = -cooling_effect + \
            economizer_effect + random.uniform(-0.05, 0.05)
        self.state.supply_temp += temp_change * dt

        # Fan status logic
        if self.state.vfd_speed > 10.0:
            self.state.fan_status = "ON"
        else:
            self.state.fan_status = "OFF"

        # Alarm generation on sensor faults (simulate randomly)
        if random.random() < 0.001:  # 0.1% chance per update
            alarms = ["High Supply Temp", "Low Airflow",
                      "Filter Alarm", "Sensor Fault"]
            self.state.alarm = random.choice(alarms)
        elif random.random() < 0.01:  # 1% chance to clear alarm
            self.state.alarm = None

    def create_telemetry_payload(self) -> Dict[str, Any]:
        """Create telemetry JSON payload"""
        return {
            "ts": int(time.time() * 1000),
            "device": self.config.get('device_id', 'ahu1'),
            "building": self.config.get('building_id', 'demo_building'),
            "points": {
                "outside_temp": round(self.state.outside_temp, 1),
                "supply_temp": round(self.state.supply_temp, 1),
                "setpoint": round(self.state.setpoint, 1),
                "vfd_speed": round(self.state.vfd_speed, 1),
                "fan_status": self.state.fan_status,
                "alarm": self.state.alarm,
                "economizer_position": round(self.state.economizer_position, 1)
            }
        }

    def publish_telemetry(self) -> None:
        """Publish telemetry data to MQTT"""
        if self.mqtt_client and self.mqtt_client.is_connected():
            topic = self.config.get('mqtt_topic', 'building/ahu1/telemetry')
            payload = self.create_telemetry_payload()

            try:
                self.mqtt_client.publish(topic, json.dumps(payload))
                logger.debug(f"Published telemetry: {payload}")
            except Exception as e:
                logger.error(f"Failed to publish telemetry: {e}")
        else:
            logger.warning("MQTT client not connected")

    def run(self, mode: str, cadence: float) -> None:
        """Main simulation loop"""
        logger.info(
            f"Starting AHU simulator in {mode} mode with {cadence}s cadence")
        self.running = True

        while self.running:
            try:
                current_time = time.time()
                dt = current_time - self.last_update
                self.last_update = current_time

                # Update outside temperature
                self.state.outside_temp = self.get_outside_temp(mode)

                # Update control logic
                self.update_control_logic(dt)

                # Publish telemetry
                self.publish_telemetry()

                # Wait for next cycle
                time.sleep(cadence)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                time.sleep(1)

        self.stop()

    def stop(self) -> None:
        """Stop the simulator"""
        logger.info("Stopping AHU simulator")
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file {config_path} not found, using defaults")
        return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AHU Simulator')
    parser.add_argument('--mode', choices=['live', 'sim'], default='sim',
                        help='Operation mode: live (real weather) or sim (simulated)')
    parser.add_argument('--cadence', type=float, default=2.0,
                        help='Telemetry publish interval in seconds')
    parser.add_argument('--config', default='simulator/config.yaml',
                        help='Path to configuration file')

    args = parser.parse_args()

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load configuration
    config = load_config(args.config)

    # Create and run simulator
    simulator = AHUSimulator(config)

    try:
        simulator.run(args.mode, args.cadence)
    except Exception as e:
        logger.error(f"Simulator error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

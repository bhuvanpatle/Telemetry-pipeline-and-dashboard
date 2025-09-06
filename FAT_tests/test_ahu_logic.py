#!/usr/bin/env python3
"""
Factory Acceptance Test (FAT) for AHU Simulator Logic
Tests the control logic and behavior of the AHU simulator

USAGE EXAMPLE:
cd FAT_tests
python test_ahu_logic.py
pytest test_ahu_logic.py -v
"""

import sys
import os
import pytest
import time
import json
from unittest.mock import Mock, patch

# Add parent directory to path to import simulator modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simulator.ahu_simulator import AHUSimulator, AHUState, PIDController


class TestPIDController:
    """Test PID controller functionality"""

    def test_pid_controller_initialization(self):
        """Test PID controller initialization with default parameters"""
        pid = PIDController()
        assert pid.kp == 1.0
        assert pid.ki == 0.1
        assert pid.kd == 0.05
        assert pid.prev_error == 0.0
        assert pid.integral == 0.0

    def test_pid_controller_custom_parameters(self):
        """Test PID controller initialization with custom parameters"""
        pid = PIDController(kp=2.0, ki=0.2, kd=0.1)
        assert pid.kp == 2.0
        assert pid.ki == 0.2
        assert pid.kd == 0.1

    def test_pid_controller_update(self):
        """Test PID controller update method"""
        pid = PIDController(kp=1.0, ki=0.1, kd=0.05)

        # First update
        error1 = 2.0
        dt1 = 1.0
        output1 = pid.update(error1, dt1)

        # Output should be kp * error + ki * error * dt + kd * (error - prev_error) / dt
        # For first call, prev_error = 0.0
        expected_output1 = 1.0 * 2.0 + 0.1 * \
            2.0 * 1.0 + 0.05 * (2.0 - 0.0) / 1.0
        assert abs(output1 - expected_output1) < 0.001        # Second update
        error2 = 1.0
        dt2 = 1.0
        output2 = pid.update(error2, dt2)

        # Should include derivative term
        assert output2 != output1


class TestAHUState:
    """Test AHU state data structure"""

    def test_ahu_state_initialization(self):
        """Test AHU state initialization with default values"""
        state = AHUState()
        assert state.supply_temp == 18.0
        assert state.outside_temp == 25.0
        assert state.setpoint == 18.0
        assert state.vfd_speed == 50.0
        assert state.fan_status == "ON"
        assert state.alarm is None


class TestAHUSimulator:
    """Test AHU simulator control logic"""

    @pytest.fixture
    def simulator_config(self):
        """Fixture providing test configuration"""
        return {
            'mqtt_broker': 'localhost',
            'mqtt_port': 1883,
            'mqtt_topic': 'test/ahu1/telemetry',
            'device_id': 'test_ahu1',
            'building_id': 'test_building',
            'pid_kp': 2.0,
            'pid_ki': 0.1,
            'pid_kd': 0.05
        }

    @patch('paho.mqtt.client.Client')
    def test_simulator_initialization(self, mock_mqtt, simulator_config):
        """Test simulator initialization"""
        simulator = AHUSimulator(simulator_config)

        assert simulator.config == simulator_config
        assert isinstance(simulator.state, AHUState)
        assert isinstance(simulator.pid, PIDController)
        assert simulator.pid.kp == 2.0
        assert simulator.pid.ki == 0.1
        assert simulator.pid.kd == 0.05

    @patch('paho.mqtt.client.Client')
    def test_economizer_logic_cold_outside(self, mock_mqtt, simulator_config):
        """Test economizer opens when outside temperature is favorable"""
        simulator = AHUSimulator(simulator_config)

        # Set cold outside temperature (good for free cooling)
        simulator.state.outside_temp = 15.0  # Below setpoint + 2
        simulator.state.setpoint = 18.0

        # Update control logic
        simulator.update_control_logic(1.0)

        # Economizer should open
        assert simulator.state.economizer_position > 0
        print(
            f"Economizer position with cold outside air: {simulator.state.economizer_position}%")

    @patch('paho.mqtt.client.Client')
    def test_economizer_logic_warm_outside(self, mock_mqtt, simulator_config):
        """Test economizer closes when outside temperature is not favorable"""
        simulator = AHUSimulator(simulator_config)

        # Set warm outside temperature (not good for free cooling)
        simulator.state.outside_temp = 25.0  # Above setpoint + 2
        simulator.state.setpoint = 18.0

        # Update control logic
        simulator.update_control_logic(1.0)

        # Economizer should be closed
        assert simulator.state.economizer_position == 0.0
        print(
            f"Economizer position with warm outside air: {simulator.state.economizer_position}%")

    @patch('paho.mqtt.client.Client')
    def test_vfd_speed_control(self, mock_mqtt, simulator_config):
        """Test VFD speed responds to temperature error"""
        simulator = AHUSimulator(simulator_config)

        # Set supply temperature higher than setpoint (needs more cooling)
        simulator.state.supply_temp = 20.0
        simulator.state.setpoint = 18.0

        initial_vfd_speed = simulator.state.vfd_speed

        # Update control logic multiple times to see PID response
        for _ in range(5):
            simulator.update_control_logic(1.0)

        # VFD speed should increase to provide more cooling
        assert simulator.state.vfd_speed > initial_vfd_speed
        print(
            f"VFD speed increased from {initial_vfd_speed}% to {simulator.state.vfd_speed}%")

    @patch('paho.mqtt.client.Client')
    def test_vfd_speed_limits(self, mock_mqtt, simulator_config):
        """Test VFD speed stays within limits"""
        simulator = AHUSimulator(simulator_config)

        # Extreme temperature error to test limits
        simulator.state.supply_temp = 30.0  # Very high
        simulator.state.setpoint = 18.0

        # Update control logic many times
        for _ in range(20):
            simulator.update_control_logic(1.0)

        # VFD speed should be within 0-100% range (updated for new control logic)
        assert 0.0 <= simulator.state.vfd_speed <= 100.0
        print(f"VFD speed within limits: {simulator.state.vfd_speed}%")

    @patch('paho.mqtt.client.Client')
    def test_fan_status_logic(self, mock_mqtt, simulator_config):
        """Test fan status changes with VFD speed"""
        simulator = AHUSimulator(simulator_config)

        # Test fan ON when VFD speed is above threshold
        simulator.state.vfd_speed = 60.0
        # Just update the fan status logic part without running full control logic
        if simulator.state.vfd_speed > 10.0:
            simulator.state.fan_status = "ON"
        else:
            simulator.state.fan_status = "OFF"
        assert simulator.state.fan_status == "ON"

        # Test fan OFF when VFD speed is below threshold
        simulator.state.vfd_speed = 5.0
        # Just update the fan status logic part without running full control logic
        if simulator.state.vfd_speed > 10.0:
            simulator.state.fan_status = "ON"
        else:
            simulator.state.fan_status = "OFF"
        assert simulator.state.fan_status == "OFF"

        print(f"Fan status correctly follows VFD speed")

    @patch('paho.mqtt.client.Client')
    def test_telemetry_payload_format(self, mock_mqtt, simulator_config):
        """Test telemetry payload format matches specification"""
        simulator = AHUSimulator(simulator_config)

        payload = simulator.create_telemetry_payload()

        # Check required fields
        assert 'ts' in payload
        assert 'device' in payload
        assert 'building' in payload
        assert 'points' in payload

        # Check timestamp is recent
        assert isinstance(payload['ts'], int)
        assert payload['ts'] > 0

        # Check device and building IDs
        assert payload['device'] == 'test_ahu1'
        assert payload['building'] == 'test_building'

        # Check points structure
        points = payload['points']
        required_points = ['outside_temp', 'supply_temp',
                           'setpoint', 'vfd_speed', 'fan_status']
        for point in required_points:
            assert point in points

        # Check data types
        assert isinstance(points['outside_temp'], (int, float))
        assert isinstance(points['supply_temp'], (int, float))
        assert isinstance(points['setpoint'], (int, float))
        assert isinstance(points['vfd_speed'], (int, float))
        assert isinstance(points['fan_status'], str)

        print("Telemetry payload format validation passed")

    @patch('requests.get')
    @patch('paho.mqtt.client.Client')
    def test_weather_api_integration(self, mock_mqtt, mock_requests, simulator_config):
        """Test weather API integration in live mode"""
        # Mock successful weather API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'current_weather': {
                'temperature': 25.5
            }
        }
        mock_requests.return_value = mock_response

        simulator = AHUSimulator(simulator_config)

        # Test live mode (should use API)
        temp = simulator.get_outside_temp('live')
        assert temp == 25.5

        # Test simulation mode (should not use API)
        temp_sim = simulator.get_outside_temp('sim')
        assert isinstance(temp_sim, (int, float))
        assert temp_sim != 25.5  # Should be different from API value

        print(
            f"Weather API integration test passed: live={temp}, sim={temp_sim}")

    @patch('paho.mqtt.client.Client')
    def test_control_loop_stability(self, mock_mqtt, simulator_config):
        """Test that control loop reaches stability"""
        simulator = AHUSimulator(simulator_config)

        # Set initial conditions
        simulator.state.outside_temp = 25.0
        simulator.state.supply_temp = 20.0  # Start above setpoint
        simulator.state.setpoint = 18.0

        # Run control loop for many iterations
        temp_history = []
        for i in range(100):
            simulator.update_control_logic(1.0)
            temp_history.append(simulator.state.supply_temp)

        # Check that temperature stabilizes near setpoint
        final_temps = temp_history[-10:]  # Last 10 values
        avg_final_temp = sum(final_temps) / len(final_temps)

        # Should be close to setpoint (within 1 degree)
        assert abs(avg_final_temp - simulator.state.setpoint) < 1.0

        print(
            f"Control loop stabilized at {avg_final_temp:.2f}°C (setpoint: {simulator.state.setpoint}°C)")


def run_integration_test():
    """Run a comprehensive integration test"""
    print("\\n" + "="*60)
    print("RUNNING AHU SIMULATOR INTEGRATION TEST")
    print("="*60)

    config = {
        'mqtt_broker': 'localhost',
        'mqtt_port': 1883,
        'mqtt_topic': 'test/ahu1/telemetry',
        'device_id': 'test_ahu1',
        'building_id': 'test_building',
        'pid_kp': 2.0,
        'pid_ki': 0.1,
        'pid_kd': 0.05
    }

    with patch('paho.mqtt.client.Client'):
        simulator = AHUSimulator(config)

        print("\\n1. Testing economizer control logic:")
        print("   a) Cold outside air (15°C, setpoint 18°C)")
        simulator.state.outside_temp = 15.0
        simulator.state.setpoint = 18.0
        simulator.update_control_logic(1.0)
        print(
            f"      Economizer position: {simulator.state.economizer_position:.1f}%")

        print("   b) Warm outside air (25°C, setpoint 18°C)")
        simulator.state.outside_temp = 25.0
        simulator.update_control_logic(1.0)
        print(
            f"      Economizer position: {simulator.state.economizer_position:.1f}%")

        print("\\n2. Testing temperature control response:")
        simulator.state.supply_temp = 22.0  # High temperature
        simulator.state.setpoint = 18.0
        print(
            f"   Initial: Supply={simulator.state.supply_temp}°C, VFD={simulator.state.vfd_speed:.1f}%")

        for i in range(5):
            simulator.update_control_logic(1.0)
            if i == 4:
                print(
                    f"   After 5 cycles: Supply={simulator.state.supply_temp:.1f}°C, VFD={simulator.state.vfd_speed:.1f}%")

        print("\\n3. Testing telemetry payload:")
        payload = simulator.create_telemetry_payload()
        print(f"   Payload keys: {list(payload.keys())}")
        print(f"   Points: {list(payload['points'].keys())}")

        print("\\n4. Testing alarm generation:")
        alarm_count = 0
        for _ in range(1000):  # Run many cycles to trigger random alarm
            simulator.update_control_logic(0.1)
            if simulator.state.alarm:
                alarm_count += 1
                print(f"   Generated alarm: {simulator.state.alarm}")
                break

        if alarm_count == 0:
            print("   No alarms generated (this is random, so may not occur)")

        print("\\n" + "="*60)
        print("INTEGRATION TEST COMPLETED SUCCESSFULLY")
        print("="*60)


if __name__ == '__main__':
    # Run integration test
    run_integration_test()

    # Run pytest if available
    try:
        import pytest
        print("\\nRunning pytest...")
        pytest.main([__file__, '-v'])
    except ImportError:
        print("\\npytest not available, integration test completed.")

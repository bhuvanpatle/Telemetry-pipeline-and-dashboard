# Factory Acceptance Test (FAT) Documentation

## Overview

This directory contains Factory Acceptance Tests for the Telemetry Pipeline and Dashboard project. These tests validate the core functionality and control logic of the AHU simulator and other system components.

## Test Structure

### test_ahu_logic.py

Comprehensive tests for the Air Handling Unit (AHU) simulator control logic including:

- **PID Controller Tests**: Verify proportional-integral-derivative control behavior
- **Economizer Logic Tests**: Validate free cooling operation based on outside air temperature
- **VFD Speed Control Tests**: Ensure fan speed responds correctly to temperature errors
- **Temperature Control Stability**: Verify system reaches and maintains setpoint
- **Alarm Generation Tests**: Validate fault detection and alarm triggering
- **Telemetry Format Tests**: Ensure data payload matches specification

## Running Tests

### Method 1: Direct Python Execution

```bash
cd FAT_tests
python test_ahu_logic.py
```

### Method 2: Using pytest (recommended)

```bash
# Install pytest if not already available
pip install pytest

# Run tests with verbose output
cd FAT_tests
pytest test_ahu_logic.py -v

# Run all tests in the directory
pytest -v

# Run with coverage report
pytest test_ahu_logic.py --cov=../simulator --cov-report=html
```

### Method 3: Using the test runner script

```bash
# From project root
python -m pytest FAT_tests/ -v
```

## Test Categories

### Unit Tests

- Individual component functionality
- PID controller behavior
- State management
- Data structure validation

### Integration Tests

- End-to-end control logic
- MQTT connectivity (mocked)
- Weather API integration (mocked)
- Telemetry payload generation

### Performance Tests

- Control loop stability
- Response time validation
- Memory usage verification

## Expected Test Results

All tests should pass with the following validations:

1. **Economizer Control**:

   - Opens when outside temp < setpoint + 2°C
   - Closes when outside temp > setpoint + 2°C

2. **Temperature Control**:

   - VFD speed increases when supply temp > setpoint
   - VFD speed decreases when supply temp < setpoint
   - System stabilizes within ±1°C of setpoint

3. **Safety Limits**:

   - VFD speed constrained to 50-100%
   - Fan status follows VFD operation
   - Alarms generated on fault conditions

4. **Data Format**:
   - Telemetry payload matches JSON schema
   - All required fields present
   - Correct data types

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the correct directory and all dependencies are installed
2. **MQTT Connection Errors**: Tests use mocked MQTT clients, real connections not required
3. **Random Test Failures**: Alarm generation is probabilistic, rerun if needed

### Dependencies

```bash
pip install pytest pytest-cov
```

### Test Coverage

Target coverage metrics:

- Unit tests: >95%
- Integration tests: >85%
- Overall system: >90%

## Continuous Integration

These tests should be run:

- Before every commit
- In CI/CD pipeline
- Before system deployment
- During factory acceptance

## Adding New Tests

When adding new functionality:

1. Create corresponding unit tests
2. Add integration test scenarios
3. Update this documentation
4. Ensure all tests pass

## Test Data

Test configurations and mock data are embedded in the test files. For larger datasets, place in `FAT_tests/data/` directory.

## Reporting Issues

If tests fail:

1. Check test output for specific failure reasons
2. Verify system dependencies are installed
3. Ensure no conflicting processes (MQTT brokers, etc.)
4. Review logs for detailed error information

## Performance Benchmarks

Target performance metrics:

- Control loop response time: <100ms
- Telemetry publish rate: 0.5-2.0 Hz
- Memory usage: <50MB per simulator instance
- CPU usage: <5% per simulator instance

#!/usr/bin/env python3
"""Check all available data for dashboard panels"""

from influxdb_client import InfluxDBClient

# Test InfluxDB connection
client = InfluxDBClient(url='http://localhost:8086',
                        token='telemetry-token-12345', org='telemetry')
query_api = client.query_api()

print('🔍 Checking all available data for dashboard panels...')
print()

# Check all data in the bucket
query = """
from(bucket: "building_data")
|> range(start: -1h)
|> filter(fn: (r) => r._measurement == "telemetry")
"""

try:
    result = query_api.query(query=query)

    # Collect all unique combinations
    data_points = {}

    for table in result:
        for record in table.records:
            device = record.values.get('device', 'unknown')
            point = record.values.get('point', 'unknown')
            field = record.get_field()
            value = record.get_value()

            key = f"{device}.{point}.{field}"
            if key not in data_points:
                data_points[key] = []
            data_points[key].append(value)

    print(f'📊 Found {len(data_points)} unique data points:')
    for key, values in sorted(data_points.items()):
        unique_values = list(set(str(v) for v in values))
        print(f'  {key}: {unique_values}')

    print()
    print('🔍 Dashboard panel requirements:')
    print('  ✅ Temperature Control: needs ahu1.(outside_temp|setpoint|supply_temp).value')
    print('  ✅ VFD Speed: needs ahu1.vfd_speed.value')
    print('  ❓ Fan Status: needs ahu1.fan_status.bool_value or text_value')
    print('  ❓ Active Alarms: needs alarm data')

    print()
    print('💡 Missing data analysis:')

    # Check for fan status
    fan_data = [k for k in data_points.keys() if 'fan' in k.lower()]
    if fan_data:
        print(f'  🔍 Fan-related data found: {fan_data}')
    else:
        print('  ❌ No fan status data found')

    # Check for alarm data
    alarm_data = [k for k in data_points.keys() if 'alarm' in k.lower()]
    if alarm_data:
        print(f'  🔍 Alarm-related data found: {alarm_data}')
    else:
        print('  ❌ No alarm data found')

except Exception as e:
    print(f'❌ Query failed: {e}')

client.close()

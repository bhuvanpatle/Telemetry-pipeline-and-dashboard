#!/usr/bin/env python3
"""Test Grafana InfluxDB queries"""

from influxdb_client import InfluxDBClient

# Test InfluxDB connection with exact same config as Grafana
client = InfluxDBClient(url='http://localhost:8086',
                        token='telemetry-token-12345', org='telemetry')
query_api = client.query_api()

print('🔍 Testing InfluxDB queries that Grafana should use...')
print()

# Test the exact query from the dashboard
query = """
from(bucket: "building_data")
|> range(start: -1h)
|> filter(fn: (r) => r._measurement == "telemetry")
|> filter(fn: (r) => r._field == "value")
|> filter(fn: (r) => r.point == "supply_temp" or r.point == "outside_temp" or r.point == "setpoint")
|> filter(fn: (r) => r.device == "ahu1")
|> limit(n: 5)
"""

try:
    result = query_api.query(query=query)
    count = 0
    for table in result:
        for record in table.records:
            count += 1
            point = record.values.get('point', 'unknown')
            value = record.get_value()
            time = record.get_time()
            print(f'✅ Found: {point} = {value} at {time}')

    if count == 0:
        print('❌ No records found with temperature query')

        # Try a broader query
        print('\n🔍 Trying broader query...')
        broad_query = """
        from(bucket: "building_data")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "telemetry")
        |> limit(n: 10)
        """

        result2 = query_api.query(query=broad_query)
        for table in result2:
            for record in table.records:
                measurement = record.values.get('_measurement', 'unknown')
                field = record.get_field()
                point = record.values.get('point', 'unknown')
                device = record.values.get('device', 'unknown')
                value = record.get_value()
                print(
                    f'📊 Record: measurement={measurement}, field={field}, point={point}, device={device}, value={value}')
    else:
        print(
            f'\n✅ Found {count} temperature records - Grafana should see this data!')

except Exception as e:
    print(f'❌ Query failed: {e}')

client.close()

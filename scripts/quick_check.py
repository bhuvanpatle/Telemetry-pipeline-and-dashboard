#!/usr/bin/env python3
"""Quick InfluxDB data check"""

from influxdb_client import InfluxDBClient

client = InfluxDBClient(url='http://localhost:8086',
                        token='telemetry-token-12345', org='telemetry')
query_api = client.query_api()

query = '''
from(bucket: "building_data")
|> range(start: -1h)
|> filter(fn: (r) => r._measurement == "telemetry")
|> limit(n: 10)
'''

try:
    result = query_api.query(query=query)
    count = 0
    for table in result:
        for record in table.records:
            count += 1
            point = record.values.get("point", "unknown")
            value = record.get_value()
            field = record.get_field()
            print(f'✅ {point}: {value} ({field})')

    print(f'\n📊 Total records found: {count}')

    if count > 0:
        print("🎉 Data flow is working!")
    else:
        print("⚠️ No data found - check if simulator is running")

except Exception as e:
    print(f"❌ Error: {e}")

finally:
    client.close()

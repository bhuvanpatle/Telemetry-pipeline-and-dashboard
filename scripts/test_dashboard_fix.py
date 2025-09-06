#!/usr/bin/env python3
"""Test dashboard after UID fix"""

import json
import requests
import base64

# Test Grafana API
headers = {
    'Authorization': f'Basic {base64.b64encode(b"admin:admin").decode("ascii")}'
}

print('🔍 Testing Grafana after UID fix...')

# Test data source
try:
    response = requests.get(
        'http://localhost:3000/api/datasources/1', headers=headers)
    if response.status_code == 200:
        ds = response.json()
        print(f'✅ Data source accessible: {ds["name"]} (UID: {ds["uid"]})')
    else:
        print(f'❌ Data source error: {response.status_code}')
except Exception as e:
    print(f'❌ Data source request failed: {e}')

# Test dashboard
try:
    response = requests.get(
        'http://localhost:3000/api/dashboards/uid/building-telemetry', headers=headers)
    if response.status_code == 200:
        dashboard = response.json()
        print(f'✅ Dashboard accessible: {dashboard["meta"]["slug"]}')

        # Check data source references in panels
        panel_count = len(dashboard["dashboard"]["panels"])
        print(f'📊 Found {panel_count} panels')

        datasource_uids = set()
        for panel in dashboard["dashboard"]["panels"]:
            if "datasource" in panel and "uid" in panel["datasource"]:
                datasource_uids.add(panel["datasource"]["uid"])

        print(f'🔗 Panel data source UIDs: {list(datasource_uids)}')

    else:
        print(f'❌ Dashboard error: {response.status_code}')
except Exception as e:
    print(f'❌ Dashboard request failed: {e}')

print()
print('📋 Next steps:')
print('1. Open http://localhost:3000/d/building-telemetry/building-telemetry-dashboard')
print('2. The dashboard should now show data!')
print('3. If still no data, check the time range in the dashboard (upper right corner)')

#!/usr/bin/env python3
"""Fix dashboard data source UIDs"""

import json

# Read the dashboard
with open('grafana/dashboards/building-telemetry.json', 'r') as f:
    dashboard = json.load(f)

# Update all data source UIDs from "influxdb" to the correct UID


def update_datasource_uid(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'datasource' and isinstance(value, dict) and value.get('uid') == 'influxdb':
                value['uid'] = 'P951FEA4DE68E13C5'
                print(f'✅ Updated datasource UID')
            else:
                update_datasource_uid(value)
    elif isinstance(obj, list):
        for item in obj:
            update_datasource_uid(item)


update_datasource_uid(dashboard)

# Write back the fixed dashboard
with open('grafana/dashboards/building-telemetry.json', 'w') as f:
    json.dump(dashboard, f, indent=2)

print('🔧 Dashboard updated with correct data source UID: P951FEA4DE68E13C5')

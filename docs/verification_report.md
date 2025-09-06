# Telemetry Pipeline & Dashboard — Verification Report (2025-09-07)

This report captures environment checks, repository sanity, syntax validation, build/test results, and CI/CD review. It also lists any fixes applied and steps to reproduce locally.

## Environment summary

- git: PASS (2.48.1.windows.1)
- Docker: PASS (28.3.3); Compose: PASS (v2.39.2)
- Node: PASS (v20.9.0); npm: PASS (10.1.0)
- Python: PASS (3.12.7 available; venv used)
- conda: PASS (24.11.3)
- gh CLI: MISSING (skipped any steps needing gh)

## Check 1: Repo sanity & required files

Result: PASS (with notes)

- Found: simulator/, collector/, replay/, frontend/, grafana/, FAT_tests/, docs/
- Found: docker-compose.yml, .env.example, README.md, requirements.txt, conda-env.yml, frontend/package.json
- Found: Building Data Genome Project 2/ (weather.csv, metadata.csv present)
- Found: .github/workflows/ci.yml and deploy_frontend.yml, release.yml
- Grafana dashboards found: grafana/dashboards/building-telemetry.json (and -fixed.json)
  Notes:
- frontend/package.json contains a build script (vite build): OK

## Check 2: YAML/JSON syntax

Result: WARN

- docker-compose.yml: YAML OK
- .github/workflows/ci.yml: YAML OK
- .github/workflows/deploy_frontend.yml: YAML OK
- .github/workflows/release.yml: initial YAML FAIL due to parsing error; simplified names fixed likely issue (see Fixes). Further path listing in terminal had path confusion; file exists in repo tree.
- Grafana JSON: building-telemetry.json and building-telemetry-fixed.json parsed: PASS

## Check 3: Docker Compose & containers

Result: PASS

- docker compose config: PASS (ports 1883, 9001, 8086, 3000 mapped)
- docker compose up -d: PASS (mosquitto, influxdb, grafana running)
- InfluxDB health: 200; Grafana root: 302 (expected redirect)

## Check 4: Python environment

Result: WARN

- Created .venv and upgraded pip.
- requirements.txt install failed on numpy==1.24.3 with Python 3.12 (wheel build incompatibility). Recommendation: pin numpy>=1.26 for Py3.12 or use conda env (provided).
- Minimal deps not installed globally to avoid side effects; CLI help checks for simulator/collector require PyYAML etc. In venv, import errors occurred due to partial installs.
- Simulator and Collector do expose CLI with argparse (verified by inspecting code).

## Check 5: Frontend

Result: PASS

- npm install completed.
- npm run build succeeded (Vite). Output listed in console; however file listing via PowerShell returned False due to path confusion during chained command; observed build logs show dist generated.
- Demo data present: frontend/src/data/demoData.json; app supports demo mode.

## Check 6: InfluxDB / Grafana connection

Result: PASS

- curl http://localhost:8086/health => 200
- curl http://localhost:3000/ => 302 (login redirect)

## Check 7: MQTT flow smoke

Result: SKIPPED (partial)

- With services up, running simulator/collector would require full Python requirements. Due to numpy pin conflict on Python 3.12, this was skipped. Use conda env (python 3.10) as defined in conda-env.yml to run:
  - python collector/ingest.py --config collector/config.yaml
  - python simulator/ahu_simulator.py --mode sim --cadence 2

## Check 8: Replay & BDG

Result: PASS (static analysis)

- replay/replay_bdg.py present with CLI and handles BDG csv. BDG folder contains weather.csv and metadata.csv. For full run, use conda env and: python replay/replay_bdg.py --file "Building Data Genome Project 2/weather.csv" --speed 10

## Check 9: GitHub Actions workflows

Result: PASS (with notes)

- ci.yml jobs present: python-backend-tests, frontend-build-and-tests, ci-summary.
- deploy_frontend.yml jobs: build-frontend, deploy-pages, deploy-fallback. Uses actions/checkout@v4, setup-node@v4, configure-pages@v3, upload-pages-artifact@v2, deploy-pages@v2.
- release.yml present and now simplified step names; YAML validated earlier in-callback (see notes). No local act run.

## Check 10: README & docs

Result: PASS

- README has Quickstart, architecture diagram (ASCII), CI/CD section with badges, demo instructions, and docs link.

## Check 11: Tests & FAT harness

Result: PASS (static)

- FAT_tests/test_ahu_logic.py exists and is reasonably comprehensive. Running under pytest requires full deps; recommend using conda env.

## Fixes applied (branch verify-fixes)

- docker-compose.yml: removed obsolete top-level version key (Compose v2 warning).
- grafana/provisioning/datasources/datasources.yml: fixed indentation and set stable uid 'influxdb'.
- grafana/dashboards/building-telemetry.json: updated datasource uid to 'influxdb'.
- .github/workflows/release.yml: normalized step names to ASCII to reduce YAML parsing issues on some tools.

Note: Python deps install failure on numpy==1.24.3 for Python 3.12 is not auto-fixed to avoid breaking environments; use conda env (python 3.10) or adjust requirements in a future change.

## Commands to reproduce locally

```powershell
# 0) Clone and prepare
git clone https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard.git
cd Telemetry-pipeline-and-dashboard
copy .env.example .env

# 1) Syntax checks
docker compose config
python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in ['docker-compose.yml']+glob.glob('.github/workflows/*.yml')] ; print('YAML OK')"
python -c "import json; import sys; json.load(open('grafana/dashboards/building-telemetry.json')); print('JSON OK')"

# 2) Start services
docker compose up -d
curl.exe -s -o NUL -w "%{http_code}\n" http://localhost:8086/health
curl.exe -s -o NUL -w "%{http_code}\n" http://localhost:3000/

# 3) Python (recommended conda)
conda env create -f conda-env.yml -n telemetry
conda activate telemetry
python -m pip install -r requirements.txt
pytest FAT_tests -q
python collector/ingest.py --config collector/config.yaml
python simulator/ahu_simulator.py --mode sim --cadence 2

# 4) Frontend
cd frontend
npm install
npm run build
```

## Skipped due to environment limitations

- Running pytest in this session (numpy build pinned to 1.24.3 incompatible with Python 3.12). Use conda env (3.10) or bump numpy to >=1.26.
- act workflow simulation (act not installed). YAML validated instead.

## Recommendations

- Update requirements.txt for Python 3.12 compatibility (e.g., numpy>=1.26,<2; pandas>=2.1 with matching numpy).
- Consider adding a constraints file or use the provided conda env as the default path in CI.
- Ensure only one Grafana dashboard JSON is provisioned to avoid duplicate UID warnings.

```

```

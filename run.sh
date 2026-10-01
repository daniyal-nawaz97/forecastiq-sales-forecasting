#!/usr/bin/env bash
# Start ForecastIQ locally: ./run.sh   then open http://localhost:8004
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Creating virtual environment and installing packages (first run only)..."
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt
fi
[ -f .env ] || cp .env.example .env
[ -f sample_data/sahara_mart_sales.csv ] || .venv/bin/python -m app.demo_data
echo "ForecastIQ running at http://localhost:${PORT:-8004}  (landing: /landing). First start tests the forecast on the demo data (~1 minute)."
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8004}"

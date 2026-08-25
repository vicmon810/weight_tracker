#!/usr/bin/env bash
set -euo pipefail

exec .venv/bin/python -m uvicorn api.health_api:app \
    --host 0.0.0.0 \
    --port 8999

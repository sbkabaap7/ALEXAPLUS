#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export GUESTGUARD_BASE_URL="http://127.0.0.1:${PORT:-8000}"
exec .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port "${PORT:-8000}" --no-access-log

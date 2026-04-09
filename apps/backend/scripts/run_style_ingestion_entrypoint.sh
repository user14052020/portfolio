#!/bin/sh
set -eu

cd /app
exec python3 scripts/run_style_ingestion.py "$@"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "=== Installing Python dependencies ==="
uv sync

echo ""
echo "=== Starting backend (http://localhost:8000) ==="
PYTHONUNBUFFERED=1 uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

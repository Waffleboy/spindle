#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/frontend"

echo "=== Installing frontend dependencies ==="
npm install

echo ""
echo "=== Starting frontend (http://localhost:5173) ==="
npm run dev

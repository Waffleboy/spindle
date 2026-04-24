# Task: Create start_local.sh

## Problem
No single command to start the full local development environment (backend + frontend).

## Solution
Created `start_local.sh` at project root that:
- Installs Python dependencies via `uv sync`
- Installs frontend dependencies via `npm install`
- Starts the FastAPI backend with `--reload` on port 8000
- Starts the Vite dev server on port 5173
- Handles graceful shutdown of both processes on Ctrl+C via trap

import os
from pathlib import Path

# Base directory is the project root (parent of backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
ORIGINALS_DIR = DATA_DIR / "originals"

# Database
DATABASE_URL = f"sqlite:///{DATA_DIR / 'taxonomy.db'}"

# LLM settings
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4-20250514")

# Ensure directories exist on import
DATA_DIR.mkdir(parents=True, exist_ok=True)
ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)

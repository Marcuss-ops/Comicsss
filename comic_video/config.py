"""
Centralized configuration — single source of truth for environment variables.

Both Python and TypeScript sides read from the same .env keys.
Node.js loads .env via dotenv before spawning Python, so these values
are inherited automatically.
"""

import os
from pathlib import Path

# Project paths (centralized — every module should use these)
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(PROJECT_ROOT / "output")))
LOGS_DIR = Path(os.environ.get("LOGS_DIR", str(PROJECT_ROOT / "logs")))
INPUTS_DIR = PROJECT_ROOT / "inputs"

# Ollama
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5vl:7b")
OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "300"))

# Bridge micro-service
BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "8081"))
BRIDGE_URL = os.environ.get("BRIDGE_URL", "")
BRIDGE_TIMEOUT_MS = int(os.environ.get("BRIDGE_TIMEOUT_MS", "90000"))

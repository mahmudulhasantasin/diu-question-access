"""Configuration settings for DIU Question MCP Server."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DIU_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.getenv("DIU_DB_PATH", DATA_DIR / "diu_questions.db"))

# Website endpoints
BASE_URL = os.getenv("DIU_BASE_URL", "https://ourdiu.com").rstrip("/")
BROWSE_URL = f"{BASE_URL}/questions/browse"
DEPARTMENTS_URL = f"{BASE_URL}/questions/departments"
QUESTION_DETAIL_URL = f"{BASE_URL}/questions"

# HTTP Client configuration
USER_AGENT = os.getenv(
    "DIU_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = float(os.getenv("DIU_REQUEST_TIMEOUT", "20.0"))
MAX_RETRIES = int(os.getenv("DIU_MAX_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("DIU_RETRY_DELAY", "1.0"))
RATE_LIMIT_DELAY = float(os.getenv("DIU_RATE_LIMIT_DELAY", "0.3"))

# MCP Server Settings
SERVER_NAME = "DIU Question MCP"
SERVER_VERSION = "1.0.0"
DEFAULT_TRANSPORT = os.getenv("DIU_MCP_TRANSPORT", "stdio")
SERVER_HOST = os.getenv("DIU_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("DIU_SERVER_PORT", "8000"))

# Logging
LOG_LEVEL = os.getenv("DIU_LOG_LEVEL", "INFO")

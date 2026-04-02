"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Create required directories
(project_root / "logs").mkdir(exist_ok=True)
(project_root / "data").mkdir(exist_ok=True)
(project_root / "models").mkdir(exist_ok=True)

# Set test environment variables
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "ERROR"
os.environ["REQUIRE_API_KEY"] = "false"

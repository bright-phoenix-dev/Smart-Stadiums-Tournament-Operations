"""
Test Runner Script
===================
Handles the special characters in the workspace directory path
by explicitly adding the project root to sys.path before running pytest.
Run with: python run_tests.py
"""

import sys
import os
from pathlib import Path

# Ensure the project root is on the Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Now run pytest programmatically
import pytest

exit_code = pytest.main([
    "backend/tests/",
    "-v",
    "--tb=short",
    "-p", "no:cacheprovider",
])

sys.exit(exit_code)

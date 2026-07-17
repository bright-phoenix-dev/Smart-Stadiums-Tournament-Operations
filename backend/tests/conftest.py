"""
Pytest configuration — adds the project root to sys.path so that
'backend' package imports work regardless of the working directory
or special characters in the path.
"""

import sys
from pathlib import Path

# Add the project root (parent of backend/) to the Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def disable_live_llm_api():
    """
    SECURITY & PERFORMANCE ISOLATION:
    Globally mocks the Gemini model getter for all test files.
    This guarantees that the test suite NEVER makes live HTTP calls to external
    LLM APIs, even if GEMINI_API_KEY is present in the developer's environment.
    All assistant queries will deterministically route to the fallback engine.
    """
    with patch("backend.services.genai_service._get_gemini_model", return_value=None):
        yield

"""Basic tests to verify imports and setup."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_python_version():
    """Test Python version."""
    assert sys.version_info >= (3, 10)


def test_imports():
    """Test basic imports."""
    import numpy as np
    assert np.__version__


def test_project_structure():
    """Test project structure exists."""
    project_root = Path(__file__).parent.parent
    
    assert (project_root / "src").exists()
    assert (project_root / "src" / "nids").exists()
    assert (project_root / "requirements.txt").exists()
    assert (project_root / "README.md").exists()


def test_validators_import():
    """Test validators can be imported."""
    from src.nids.utils.validators import validate_ip_address
    
    # Test valid IPs
    assert validate_ip_address("192.168.1.1") is True
    assert validate_ip_address("10.0.0.1") is True
    
    # Test invalid IPs
    assert validate_ip_address("999.999.999.999") is False
    assert validate_ip_address("invalid") is False


def test_exceptions_exist():
    """Test exception classes exist."""
    from src.nids.utils.exceptions import (
        NIDSException,
        ModelNotLoadedException,
        InferenceException,
    )
    
    assert NIDSException
    assert ModelNotLoadedException
    assert InferenceException

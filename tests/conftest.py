from pathlib import Path

import pytest

import pdbstore


@pytest.fixture(scope="session")
def test_dir(pytestconfig) -> Path:
    """Retrieve path to tests directory from test environment"""
    return pytestconfig.rootdir / "tests"


@pytest.fixture(scope="session")
def test_data_dir(pytestconfig) -> Path:
    """Retrieve path to tests directory from test environment"""
    return pytestconfig.rootdir / "tests" / "data"


@pytest.fixture(autouse=True)
def default_files(monkeypatch):
    """Ensures user configuration files do not interfere with tests."""
    monkeypatch.setattr(pdbstore.config, "_DEFAULT_CONFIG_FILES", [])

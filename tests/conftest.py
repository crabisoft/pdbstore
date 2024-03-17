import shutil
from pathlib import Path

import pytest

import pdbstore
from pdbstore.typing import Generator


@pytest.fixture(scope="session")
def test_dir(pytestconfig) -> Path:
    """Retrieve path to tests directory from test environment"""
    return pytestconfig.rootdir / "tests"


@pytest.fixture(scope="session")
def test_data_dir(pytestconfig) -> Path:
    """Retrieve path to tests data directory from test environment"""
    return pytestconfig.rootdir / "tests" / "data"


@pytest.fixture(scope="session")
def test_data_native_dir(pytestconfig) -> Path:
    """Retrieve path to native tests data directory from test environment"""
    return pytestconfig.rootdir / "tests" / "data" / "native"


@pytest.fixture(scope="session")
def test_data_portable_dir(pytestconfig) -> Path:
    """Retrieve path to portable tests data directory from test environment"""
    return pytestconfig.rootdir / "tests" / "data" / "portable"


@pytest.fixture(scope="session")
def test_data_invalid_dir(pytestconfig) -> Path:
    """Retrieve path to invalid tests data directory from test environment"""
    return pytestconfig.rootdir / "tests" / "data" / "invalid"


@pytest.fixture(autouse=True)
def default_files(monkeypatch):
    """Ensures user configuration files do not interfere with tests."""
    monkeypatch.setattr(pdbstore.config, "_DEFAULT_CONFIG_FILES", [])


@pytest.fixture(name="tmp_store_dir")
def fixture_tmp_store_dir(tmp_path) -> Generator[Path, None, None]:
    """Generate temporary history file"""
    local_store_dir = tmp_path / "store"
    local_store_dir.mkdir(parents=True)
    yield local_store_dir
    shutil.rmtree(local_store_dir)


@pytest.fixture
def tmp_store(tmp_store_dir) -> Generator[pdbstore.Store, None, None]:
    """Generate temporary history file"""
    store = pdbstore.Store(tmp_store_dir)
    yield store


@pytest.fixture(name="tmp_store_input_dir")
def fixture_tmp_store_input_dir(tmp_path) -> Generator[Path, None, None]:
    """Generate temporary history file"""
    local_store_dir = tmp_path / "store_in"
    local_store_dir.mkdir(parents=True)
    yield local_store_dir
    shutil.rmtree(local_store_dir)


@pytest.fixture
def tmp_store_input(tmp_store_input_dir) -> Generator[pdbstore.Store, None, None]:
    """Generate temporary history file"""
    store = pdbstore.Store(tmp_store_input_dir)
    yield store


@pytest.fixture(name="dynamic_config_file")
def fixture_dynamic_config_file(tmp_path, tmp_store_dir) -> Generator[Path, None, None]:
    """Generate temporary configuration file"""
    config_path = tmp_path / "config.cfg"

    valid_config = f"""[global]
    default = release
    keep = 1

    [release]
    store = {tmp_store_dir}/release

    [snapshot]
    store = {tmp_store_dir}/snapshot
    keep = 30
    """
    config_path.write_text(valid_config)
    yield config_path
    config_path.unlink()


@pytest.fixture(name="dynamic_config_object")
def fixture_dynamic_config_object(dynamic_config_file: Path) -> pdbstore.config.ConfigParser:
    """Generate temporary configuration file"""
    config = pdbstore.config.ConfigParser(None, [dynamic_config_file])
    return config

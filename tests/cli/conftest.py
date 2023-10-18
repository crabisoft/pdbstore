import shutil
from pathlib import Path

import pytest


@pytest.fixture(name="tmp_store_path")
def fixture_tmp_store_path(tmp_path) -> Path:
    """Generate temporary history file"""
    tmp_store_dir = tmp_path / "store"
    tmp_store_dir.mkdir(parents=True)
    yield tmp_store_dir
    shutil.rmtree(tmp_store_dir)


@pytest.fixture
def dynamic_config_file(tmp_path, tmp_store_path) -> Path:
    """Generate temporary configuration file"""
    config_path = tmp_path / "config.cfg"

    valid_config = f"""[global]
    default = release
    keep = 1

    [release]
    store = {tmp_store_path}/release

    [snapshot]
    store = {tmp_store_path}/snapshot
    keep = 30
    """
    config_path.write_text(valid_config)
    yield config_path
    config_path.unlink()

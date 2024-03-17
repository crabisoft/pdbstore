import io
from pathlib import Path
from unittest import mock

import pytest

import pdbstore
from pdbstore import config, exceptions

NO_DEFAULT_CONFIG = """[global]
[release]
store = /some/where
keep = 1
"""

VALID_CONFIG = """[global]
default = release
keep = 1

[release]
store = /some/where/release

[snapshot]
store = /some/where/snapshot
keep = 30

[myproduct]
store = /some/myproduct
keep = 15
product = oneproduct
"""

INVALID_DATA_CONFIG = """[global]
[release]
store = /some/where/release

[noroot]
keep = 1

[nokeep]
store = /some/where
keep = ten

[nocompress]
store = /some/where
compress = ten

"""

INVALID_GLOBAL_KEEP = """[global]
default = release
keep = ten
[release]
store = /some/where/release
keep = 1
"""
INVALID_GLOBAL_COMPRESS = """[global]
default = release
compress = ten
[release]
store = /some/where/release
keep = 1
"""


# pylint: disable=protected-access


@pytest.fixture(autouse=True, name="default_files")
def fixture_default_files(monkeypatch):
    """Overrides mocked default files from conftest.py as we have our own mocks here."""
    monkeypatch.setattr(pdbstore.config, "_DEFAULT_CONFIG_FILES", config._DEFAULT_CONFIG_FILES)


def _mock_nonexistent_file(*_, **__):
    raise OSError


def _mock_existent_file(path, *_, **__):
    return path


def test_env_config_missing_file_raises(monkeypatch):
    """test missing config file"""
    monkeypatch.setenv("PDBSTORE_CFG", "/invalid/path")
    with pytest.raises(exceptions.ConfigMissingError):
        config._get_config_files()


def test_env_config_not_defined_does_not_raise(monkeypatch):
    """test not valid config files"""
    with monkeypatch.context() as mpc:
        mpc.delenv("PDBSTORE_CFG", False)
        mpc.setattr(config, "_DEFAULT_CONFIG_FILES", [])
        assert not config._get_config_files()


def test_env_config_defined(monkeypatch):
    """test valid config through env var"""
    with monkeypatch.context() as mpc:
        monkeypatch.setenv("PDBSTORE_CFG", "/valid/path")
        mpc.setattr(Path, "resolve", _mock_existent_file)
        mpc.setattr(config, "_DEFAULT_CONFIG_FILES", [])
        assert config._get_config_files() == [str(Path("/valid/path").resolve(strict=True))]


def test_env_config_valid_user_defined(monkeypatch):
    """test valid config through input path"""
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "resolve", _mock_existent_file)
        mpc.setattr(config, "_DEFAULT_CONFIG_FILES", [])
        assert config._get_config_files(["/valid/path"]) == [
            str(Path("/valid/path").resolve(strict=True))
        ]


def test_env_config_invalid_user_defined(monkeypatch):
    """test invalid config through input file"""
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "resolve", _mock_nonexistent_file)
        mpc.setattr(config, "_DEFAULT_CONFIG_FILES", [])
        with pytest.raises(exceptions.ConfigMissingError):
            config._get_config_files(["/valid/path"])


def test_default_config(monkeypatch):
    """test default configuration"""
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "resolve", _mock_nonexistent_file)
        cpo = config.ConfigParser()

    assert cpo.store_id is None
    assert cpo.store_dir is None
    assert cpo.keep_count == 0
    assert cpo.compress is False
    assert cpo.product_name is None
    assert cpo.product_version is None


def test_merge_config(monkeypatch):
    """test merge configuration"""
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "resolve", _mock_nonexistent_file)
        cpo = config.ConfigParser()
    cpo.merge(
        {
            "store_dir": "/my/custom/dir",
            "keep_count": 10,
            "compress": True,
            "product_name": "myname",
            "product_version": "1.0",
        }
    )
    assert cpo.store_id is None
    assert cpo.store_dir == "/my/custom/dir"
    assert cpo.keep_count == 10
    assert cpo.compress is True
    assert cpo.product_name == "myname"
    assert cpo.product_version == "1.0"


def test_invalid_id_without_files():
    """test invalid section name without files"""
    with pytest.raises(exceptions.ConfigMissingError):
        config.ConfigParser("release")


@mock.patch("builtins.open")
def test_invalid_id_with_files(_open, monkeypatch):
    """test invalid section name"""
    fds = io.StringIO(NO_DEFAULT_CONFIG)
    fds.close = mock.Mock(return_value=None)
    _open.return_value = fds
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "resolve", _mock_existent_file)
        config.ConfigParser("release")
        with pytest.raises(exceptions.ConfigIDError):
            config.ConfigParser()
        fds = io.StringIO(VALID_CONFIG)
        fds.close = mock.Mock(return_value=None)
        _open.return_value = fds
        with pytest.raises(exceptions.ConfigIDError):
            config.ConfigParser("not_present")


@mock.patch("builtins.open")
def test_invalid_data(_open, monkeypatch):
    """test invalid config file content"""
    fds = io.StringIO(INVALID_DATA_CONFIG)
    fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))
    _open.return_value = fds

    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "resolve", _mock_existent_file)
        config.ConfigParser("release")

        with pytest.raises(config.ConfigDataError) as exc:
            config.ConfigParser("noroot")
        assert "Impossible to get symbol store directory" in str(exc.value)

        with pytest.raises(config.ConfigDataError) as exc:
            config.ConfigParser("nokeep")
        assert "Invalid value detected for keep entry from" in str(exc.value)

        with pytest.raises(config.ConfigDataError) as exc:
            config.ConfigParser("nocompress")
        assert "Invalid value detected for compress entry from" in str(exc.value)

        with pytest.raises(config.ConfigIDError) as exc:
            config.ConfigParser("sectionnotfound")
        assert "Impossible to get symbol store details from configuration (sectionnotfound)" in str(
            exc.value
        )


@mock.patch("builtins.open")
def test_invalid_global_config(_open, monkeypatch):
    """test invalid global configuration"""
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "resolve", _mock_existent_file)

        fds = io.StringIO(INVALID_GLOBAL_KEEP)
        fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))
        _open.return_value = fds

        with pytest.raises(config.ConfigDataError) as exc:
            config.ConfigParser()
        assert "Invalid value detected for keep entry from" in str(exc.value)

        fds = io.StringIO(INVALID_GLOBAL_COMPRESS)
        fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))
        _open.return_value = fds

        with pytest.raises(config.ConfigDataError) as exc:
            config.ConfigParser()
        assert "Invalid value detected for compress entry from" in str(exc.value)


@mock.patch("builtins.open")
def test_valid_get_store_directory(_open, monkeypatch):
    """test get_store_directory behavior for valid execution"""
    fds = io.StringIO(VALID_CONFIG)
    fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))
    _open.return_value = fds
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "resolve", _mock_existent_file)
        cfg = config.ConfigParser("release")
        assert "/some/where/release" == cfg.get_store_directory("release")


@mock.patch("builtins.open")
def test_invalid_get_store_directory(_open, monkeypatch):
    """test get_store_directory behavior for invalid execution"""
    fds = io.StringIO(INVALID_DATA_CONFIG)
    fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))
    _open.return_value = fds
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "resolve", _mock_existent_file)
        cfg = config.ConfigParser("release")

        with pytest.raises(exceptions.ConfigIDError):
            cfg.get_store_directory("not_present")
        with pytest.raises(exceptions.ConfigDataError):
            cfg.get_store_directory("noroot")

    cfg = config.ConfigParser()
    assert cfg.get_store_directory("release") is None

from pathlib import Path
from unittest import mock

import pytest

from pdbstore import store
from pdbstore.cli import cli
from pdbstore.cli.exit_codes import (
    ERROR_COMMAND_NAME,
    ERROR_ENCOUNTERED,
    ERROR_GENERAL,
    ERROR_UNEXPECTED,
    SUCCESS,
)
from pdbstore.io import cab


def test_incomplete_no_action():
    """test empty command-line"""

    with mock.patch("sys.argv", []):
        assert cli.main() == ERROR_COMMAND_NAME


@pytest.mark.parametrize(
    "argv",
    [
        ["--store-dir", "/user/a/dir"],
        ["--product-name", "myproduct"],
        ["--product-version", "1.0.0"],
        [
            "--store-dir",
            "/user/a/dir",
            "--product-name",
            "myproduct",
        ],
        [
            "--store-dir",
            "/user/a/dir",
            "--product-name",
            "myproduct",
            "--product-version",
            "1.0.0",
        ],
    ],
)
def test_incomplete(argv):
    """test empty command-line"""

    # Test through direct command-line
    with mock.patch("sys.argv", ["pdbstore", "add"] + argv):
        assert cli.main() == ERROR_UNEXPECTED

    # Test with direct call to main function
    assert cli.main(["add"] + argv) == ERROR_UNEXPECTED


def test_complete(tmp_store_dir, test_data_native_dir):
    """test complete command-line"""

    argv = [
        "--store-dir",
        str(tmp_store_dir),
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        str(test_data_native_dir / "dummyapp.pdb"),
    ]

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "add"] + argv,
    ):
        assert store.Store(tmp_store_dir).next_transaction_id == "0000000001"
        assert len(store.Store(tmp_store_dir).history) == 0
        assert cli.main() == SUCCESS
        assert len(store.Store(tmp_store_dir).history) == 1
        assert store.Store(tmp_store_dir).next_transaction_id == "0000000002"

    # Test with direct call to main function
    assert cli.main(["add"] + argv) == SUCCESS
    assert store.Store(tmp_store_dir).next_transaction_id == "0000000003"
    assert len(store.Store(tmp_store_dir).history) == 2


def test_complete_with_invalid_file(tmp_store_dir, test_data_invalid_dir):
    """test complete command-line"""

    argv = [
        "--store-dir",
        str(tmp_store_dir),
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        str(test_data_invalid_dir / "bad.exe"),
    ]

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "add"] + argv,
    ):
        assert cli.main() == ERROR_ENCOUNTERED

    # Test with direct call to main function
    assert cli.main(["add"] + argv) == ERROR_ENCOUNTERED


def test_complete_with_config(dynamic_config_file, test_data_native_dir):
    """test complete command-line with configuration file usage"""
    argv = [
        "--config-file",
        str(dynamic_config_file),
        "--store",
        "release",
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        str(test_data_native_dir / "dummyapp.pdb"),
    ]

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "add"] + argv,
    ):
        assert cli.main() == SUCCESS

    # Test with direct call to main function
    assert cli.main(["add"] + argv) == SUCCESS


@mock.patch("pdbstore.io.is_compression_supported", mock.MagicMock(return_value=False))
def test_no_compression(tmp_store_dir, test_data_native_dir):
    """Test when comporession not supported"""
    argv = [
        "--store-dir",
        str(tmp_store_dir),
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        "--compress",
        str(test_data_native_dir / "dummyapp.pdb"),
    ]

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "add"] + argv,
    ):
        assert cli.main() == ERROR_GENERAL

    # Test with direct call to main function
    assert cli.main(["add"] + argv) == ERROR_GENERAL


@pytest.mark.skipif(cab.compress is None, reason="compression not available")
def test_valid_compression(tmp_store_dir, test_data_native_dir):
    """test add command when compression is supported"""
    argv = [
        "--store-dir",
        str(tmp_store_dir),
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        "--compress",
        str(test_data_native_dir / "dummyapp.pdb"),
    ]

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "add"] + argv,
    ):
        assert cli.main() == SUCCESS

    stored_path: Path = (
        tmp_store_dir / "dummyapp.pdb" / "DBF7CE25C6DC4E0EA9AD889187E296A21" / "dummyapp.pd_"
    )
    assert stored_path.exists() is True
    with stored_path.open("rb") as fpsp:
        assert fpsp.read(4) == b"MSCF"

    # Test with direct call to main function
    assert cli.main(["add"] + argv) == SUCCESS

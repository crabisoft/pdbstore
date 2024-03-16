from unittest import mock

import pytest

from pdbstore import cli, store
from pdbstore.cli.exit_codes import (
    ERROR_ENCOUNTERED,
    ERROR_GENERAL,
    ERROR_UNEXPECTED,
    SUCCESS,
)


@pytest.mark.parametrize(
    "argv",
    [
        ["--store-dir", "/user/a/dir"],
        ["1"],
    ],
)
def test_incomplete(argv):
    """test empty command-line"""

    # Test through direct command-line
    with mock.patch("sys.argv", ["pdbstore", "del"] + argv):
        assert cli.cli.main() == ERROR_UNEXPECTED

    # Test with direct call to main function
    assert cli.cli.main(["del"] + argv) == ERROR_UNEXPECTED


def test_complete(capsys, tmp_store_dir, test_data_native_dir):
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

    # Test through direct command-line when file not present yet
    with mock.patch(
        "sys.argv",
        ["pdbstore", "del", "1"] + argv[0:2],
    ):
        assert cli.cli.main() == ERROR_ENCOUNTERED
        captured = capsys.readouterr()
        assert "Number of errors = 1" in captured.out
        assert "ERROR: ID 0000000001 doesn't exist" in captured.err

    # Test with direct call to main function  when file not present yet
    assert cli.cli.main(["del", "2"] + argv[0:2]) == ERROR_ENCOUNTERED
    captured = capsys.readouterr()
    assert "Number of errors = 1" in captured.out
    assert "ERROR: ID 0000000002 doesn't exist" in captured.err

    # New file into the store and twice to have 2 records
    assert cli.cli.main(["add"] + argv) == 0
    assert len(store.Store(tmp_store_dir).history) == ERROR_GENERAL
    assert cli.cli.main(["add"] + argv) == 0
    assert len(store.Store(tmp_store_dir).history) == 2

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "del", "1"] + argv[0:2],
    ):
        assert cli.cli.main() == SUCCESS
        assert len(store.Store(tmp_store_dir).history) == 3

    # Test with direct call to main function
    assert cli.cli.main(["del", "2"] + argv[0:2]) == SUCCESS
    assert len(store.Store(tmp_store_dir).history) == 4


def test_complete_with_config(dynamic_config_file, test_data_native_dir):
    """test complete command-line with configuration file usage"""
    argv = [
        "--config-file",
        str(dynamic_config_file),
        "--store",
        "snapshot",
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        str(test_data_native_dir / "dummyapp.pdb"),
    ]

    # New file into the store and twice to have 2 records
    assert cli.cli.main(["add"] + argv) == SUCCESS
    assert cli.cli.main(["add"] + argv) == SUCCESS

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "del", "1"] + argv[0:4],
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function
    assert cli.cli.main(["del", "2"] + argv[0:4]) == SUCCESS

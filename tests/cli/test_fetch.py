import os
import re
from unittest import mock

import pytest

from pdbstore import cli
from pdbstore.cli.exit_codes import ERROR_ENCOUNTERED, ERROR_UNEXPECTED, SUCCESS


@pytest.mark.parametrize(
    "argv",
    [
        [""],
        ["--store-dir", "/user/a/dir"],
        ["/user/file"],
    ],
)
def test_incomplete(argv):
    """test empty command-line"""

    # Test through direct command-line
    with mock.patch("sys.argv", ["pdbstore", "fetch"] + argv):
        assert cli.cli.main() == ERROR_UNEXPECTED

    # Test with direct call to main function
    assert cli.cli.main(["fetch"] + argv) == ERROR_UNEXPECTED


def test_complete(capsys, tmp_store_path, test_data_dir):
    """test complete command-line"""
    pdb_path = str(test_data_dir / "dummyapp.pdb")
    exe_path = str(test_data_dir / "dummyapp.exe")

    argv = [
        "--store-dir",
        str(tmp_store_path),
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        pdb_path,
    ]

    # Test through direct command-line when file not present yet
    with mock.patch(
        "sys.argv",
        [
            "pdbstore",
            "fetch",
        ]
        + argv[0:2]
        + [exe_path],
    ):
        assert cli.cli.main() == ERROR_ENCOUNTERED
        print(str(capsys.readouterr().out))
        assert (
            re.search(r"dummyapp.exe\s+Not found", capsys.readouterr().out) is not None
        )

    # Test with direct call to main function when file not present yet
    assert cli.cli.main(["fetch"] + argv[0:2] + [exe_path]) == ERROR_ENCOUNTERED

    # New file into the store
    assert cli.cli.main(["add"] + argv) == SUCCESS

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        [
            "pdbstore",
            "fetch",
        ]
        + argv[0:2]
        + [exe_path],
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function
    assert cli.cli.main(["fetch"] + argv[0:2] + [exe_path]) == SUCCESS


@pytest.mark.parametrize(
    "filename",
    [
        "dummyapp.exe",
        "dummylib.dll",
    ],
)
def test_complete_with_config(dynamic_config_file, test_data_dir, filename):
    """test complete command-line with configuration file usage"""
    pdb_path = str(test_data_dir / (os.path.splitext(filename)[0] + ".pdb"))
    exe_path = str(test_data_dir / filename)
    argv = [
        "--config-file",
        str(dynamic_config_file),
        "--store",
        "release",
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        pdb_path,
    ]

    # New file into the store and twice to have 2 records
    assert cli.cli.main(["add"] + argv) == SUCCESS

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "fetch"] + argv[0:4] + [exe_path],
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function
    assert cli.cli.main(["fetch"] + argv[0:4] + [exe_path]) == SUCCESS

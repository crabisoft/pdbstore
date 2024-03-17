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


def test_complete(capsys, tmp_store_dir, test_data_native_dir):
    """test complete command-line"""
    pdb_path = str(test_data_native_dir / "dummyapp.pdb")
    exe_path = str(test_data_native_dir / "dummyapp.exe")

    argv = [
        "--store-dir",
        str(tmp_store_dir),
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
        assert cli.cli.main() == SUCCESS
        assert re.search(r"dummyapp.exe\s+Not found", capsys.readouterr().out) is not None

    # Test with direct call to main function when file not present yet
    assert cli.cli.main(["fetch"] + argv[0:2] + [exe_path]) == SUCCESS

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
def test_complete_with_config(dynamic_config_file, test_data_native_dir, filename):
    """test complete command-line with configuration file usage"""
    pdb_path = str(test_data_native_dir / (os.path.splitext(filename)[0] + ".pdb"))
    pe_path = str(test_data_native_dir / filename)
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
        ["pdbstore", "fetch"] + argv[0:4] + [pe_path],
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function
    assert cli.cli.main(["fetch"] + argv[0:4] + [pe_path]) == SUCCESS


@pytest.mark.parametrize(
    "formatter",
    [
        ["-f", "text"],
        ["-f", "json"],
    ],
)
def test_multiple_with_config(dynamic_config_file, test_data_native_dir, formatter):
    """test multiple files with different formatters"""
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
        str(test_data_native_dir / "dummylib.pdb"),
    ]
    pe_list = [
        str(test_data_native_dir / "dummyapp.exe"),
        str(test_data_native_dir / "dummylib.dll"),
    ]
    nf_path = str(test_data_native_dir / "notfound.pdb")
    script_path = __file__

    # New file into the store
    assert cli.cli.main(["add"] + argv + ["-VVV"]) == SUCCESS

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "fetch"] + formatter + argv[0:4] + pe_list,
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function
    assert cli.cli.main(["fetch"] + formatter + argv[0:4] + pe_list[0:1]) == SUCCESS
    assert cli.cli.main(["fetch", "-F"] + formatter + argv[0:4] + pe_list) == SUCCESS

    assert (
        cli.cli.main(["fetch"] + formatter + argv[0:4] + pe_list + [nf_path]) == ERROR_ENCOUNTERED
    )
    assert cli.cli.main(["fetch"] + formatter + argv[0:4] + pe_list + [script_path]) == SUCCESS

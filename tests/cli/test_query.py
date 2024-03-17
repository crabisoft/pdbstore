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
    with mock.patch("sys.argv", ["pdbstore", "query"] + argv):
        assert cli.cli.main() == ERROR_UNEXPECTED

    # Test with direct call to main function
    assert cli.cli.main(["query"] + argv) == ERROR_UNEXPECTED


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
        [
            "pdbstore",
            "query",
        ]
        + argv[0:2]
        + argv[-1:],
    ):
        assert cli.cli.main() == ERROR_ENCOUNTERED
        assert re.search(r"dummyapp.pdb\s+Not found", capsys.readouterr().out) is not None

    # Test with direct call to main function when file not present yet
    assert cli.cli.main(["query"] + argv[0:2] + argv[-1:]) == ERROR_ENCOUNTERED

    # New file into the store
    assert cli.cli.main(["add"] + argv) == SUCCESS

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        [
            "pdbstore",
            "query",
        ]
        + argv[0:2]
        + argv[-1:],
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function
    assert cli.cli.main(["query"] + argv[0:2] + argv[-1:]) == SUCCESS


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

    # New file into the store and twice to have 2 records
    assert cli.cli.main(["add"] + argv) == SUCCESS

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "query"] + argv[0:4] + argv[-1:],
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function
    assert cli.cli.main(["query"] + argv[0:4] + argv[-1:]) == SUCCESS


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

    # New file into the store
    assert cli.cli.main(["add"] + argv) == SUCCESS

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "query"] + formatter + argv[0:4] + argv[-2:-1],
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function
    assert cli.cli.main(["query"] + formatter + argv[0:4] + argv[-2:-1]) == SUCCESS
    assert cli.cli.main(["query", "-F"] + formatter + argv[0:4] + argv[-2:]) == SUCCESS

    assert (
        cli.cli.main(
            ["query"]
            + formatter
            + argv[0:4]
            + argv[-2:]
            + [str(test_data_native_dir / "notfound.pdb")]
        )
        == ERROR_ENCOUNTERED
    )
    assert (
        cli.cli.main(["query"] + formatter + argv[0:4] + argv[-2:] + [str(__file__)])
        == ERROR_ENCOUNTERED
    )

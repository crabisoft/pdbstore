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


def test_complete(capsys, tmp_store_path, test_data_dir):
    """test complete command-line"""

    argv = [
        "--store-dir",
        str(tmp_store_path),
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        str(test_data_dir / "dummyapp.pdb"),
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
        print(
            "cmdline=",
            [
                "pdbstore",
                "query",
            ]
            + argv[0:2]
            + argv[-1:],
        )
        print(capsys.readouterr().out)
        assert cli.cli.main() == ERROR_ENCOUNTERED
        assert (
            re.search(r"dummyapp.pdb\s+Not found", capsys.readouterr().out) is not None
        )

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


def test_complete_with_config(dynamic_config_file, test_data_dir):
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
        str(test_data_dir / "dummyapp.pdb"),
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

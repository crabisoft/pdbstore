import time
from unittest import mock

import pytest

from pdbstore import cli
from pdbstore.cli.exit_codes import ERROR_UNEXPECTED, SUCCESS


@pytest.mark.parametrize(
    "argv",
    [
        [""],
        ["--store-dir", "/user/a/dir"],
        ["2023-11-17"],
    ],
)
def test_incomplete(argv):
    """test empty command-line"""

    # Test through direct command-line
    with mock.patch("sys.argv", ["pdbstore", "unused"] + argv):
        assert cli.cli.main() == ERROR_UNEXPECTED

    # Test with direct call to main function
    assert cli.cli.main(["unused"] + argv) == ERROR_UNEXPECTED


def test_complete(capsys, tmp_store_dir, test_data_native_dir):
    """test complete command-line"""
    tomorrow = time.strftime("%Y-%m-%d", time.localtime(time.time() + 3600 * 24))
    pdb_path = str(test_data_native_dir / "dummyapp.pdb")
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
            "unused",
        ]
        + argv[0:2]
        + [tomorrow],
    ):
        assert cli.cli.main() == SUCCESS
        out, err = capsys.readouterr()
        assert "" == out
        assert "" == err

    # Test with direct call to main function when file not present yet
    assert cli.cli.main(["unused"] + argv[0:2] + [tomorrow]) == SUCCESS
    out, err = capsys.readouterr()
    assert "" == out
    assert "" == err

    # New file into the store
    assert cli.cli.main(["add", "-Vquiet"] + argv) == SUCCESS

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        [
            "pdbstore",
            "unused",
        ]
        + argv[0:2]
        + [tomorrow],
    ):
        assert cli.cli.main() == SUCCESS
        out, err = capsys.readouterr()
        assert "" != out
        assert "" == err

    # Test with direct call to main function
    assert cli.cli.main(["unused"] + argv[0:2] + [tomorrow]) == SUCCESS
    out, err = capsys.readouterr()
    assert "" != out
    assert "" == err


@pytest.mark.parametrize(
    "formatter",
    [
        ["-f", "text", "", f"{'Input File':<{80}s}{'Date':^10s}  Transaction ID"],
        ["-f", "json", "[]\n", '[\n    {\n        "status": "success"'],
    ],
)
def test_multiple_with_config(capsys, dynamic_config_file, test_data_native_dir, formatter):
    """test multiple files with different formatters"""
    pdb_path = str(test_data_native_dir / "dummylib.pdb")
    tomorrow = time.strftime("%Y-%m-%d", time.localtime(time.time() + 3600 * 24))
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

    assert cli.cli.main(["unused"] + formatter[0:2] + argv[0:4] + [tomorrow]) == SUCCESS
    out, err = capsys.readouterr()
    assert formatter[2] == out
    assert "" == err

    # New file into the store
    assert cli.cli.main(["add", "-Vquiet"] + argv) == SUCCESS
    _, _ = capsys.readouterr()

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "unused"] + formatter[0:2] + argv[0:4] + [tomorrow],
    ):
        assert cli.cli.main() == SUCCESS
        out, err = capsys.readouterr()
        assert out.startswith(formatter[3])
        assert "" == err

    # Test with direct call to main function
    assert cli.cli.main(["unused"] + formatter[0:2] + argv[0:4] + [tomorrow]) == SUCCESS

    assert (
        cli.cli.main(["unused"] + formatter[0:2] + argv[0:4] + ["1970-15-05"]) == ERROR_UNEXPECTED
    )

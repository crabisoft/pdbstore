from unittest import mock

import pytest

from pdbstore import cli
from pdbstore.cli.exit_codes import ERROR_SUBCOMMAND_NAME, ERROR_UNEXPECTED, SUCCESS


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--format", "text"],
    ],
)
def test_incomplete(argv):
    """test empty command-line"""

    # Test through direct command-line
    with mock.patch("sys.argv", ["pdbstore", "report", "file"] + argv):
        assert cli.cli.main() == ERROR_UNEXPECTED

    # Test with direct call to main function
    assert cli.cli.main(["report", "product"] + argv) == ERROR_UNEXPECTED


def test_no_options():
    """Test through direct command-line without command name"""
    with mock.patch("sys.argv", ["pdbstore", "report", "junk"]):
        assert cli.cli.main() == ERROR_SUBCOMMAND_NAME


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

    # Test through direct command-line when file not present yet
    with mock.patch(
        "sys.argv",
        ["pdbstore", "report", "product"] + argv[0:2],
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function when file not present yet
    assert cli.cli.main(["report", "product"] + argv[0:2]) == SUCCESS

    # New file into the store
    assert cli.cli.main(["add"] + argv) == SUCCESS

    # Test through direct command-line
    with mock.patch(
        "sys.argv",
        ["pdbstore", "report", "file"] + argv[0:2],
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function
    assert cli.cli.main(["report", "transaction"] + argv[0:2]) == SUCCESS


@pytest.mark.parametrize("report_type", ["product", "file", "transaction"])
def test_report_types(report_type, tmp_store_dir, test_data_native_dir):
    """test all supported report types"""

    # Generate temporary store
    argv = [
        "--store-dir",
        str(tmp_store_dir),
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        str(test_data_native_dir / "dummyapp.pdb"),
    ]
    assert cli.cli.main(["add"] + argv) == SUCCESS
    assert cli.cli.main(["report", report_type] + argv[0:2]) == SUCCESS


@pytest.mark.parametrize(
    "out_format",
    ["text", "markdown", "json", "html"],
)
def test_report_formats(out_format, tmp_path, tmp_store_dir, test_data_native_dir):
    """test all supported report types"""

    # Generate temporary store
    argv = [
        "--store-dir",
        str(tmp_store_dir),
        "--product-name",
        "myproduct",
        "--product-version",
        "1.0.0",
        str(test_data_native_dir / "dummyapp.pdb"),
    ]
    assert cli.cli.main(["add"] + argv) == SUCCESS
    report_path = tmp_path / "test.report"
    ext_arg = ["-o", str(report_path), "--format", out_format]
    assert cli.cli.main(["report", "file"] + argv[0:2] + ext_arg) == SUCCESS
    assert report_path.is_file() is True
    report_path.unlink(missing_ok=True)
    assert cli.cli.main(["report", "product"] + argv[0:2] + ext_arg) == SUCCESS
    assert report_path.is_file() is True
    report_path.unlink(missing_ok=True)
    assert cli.cli.main(["report", "transaction"] + argv[0:2] + ext_arg) == SUCCESS
    assert report_path.is_file() is True
    report_path.unlink(missing_ok=True)

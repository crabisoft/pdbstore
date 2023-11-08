from unittest import mock

import pytest

from pdbstore import cli
from pdbstore.cli.exit_codes import ERROR_UNEXPECTED, SUCCESS
from pdbstore.store import Store, TransactionType


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
        ],
    ],
)
def test_incomplete(argv):
    """test incomplete command-line"""

    # Test through direct command-line
    with mock.patch("sys.argv", ["pdbstore", "clean"] + argv):
        assert cli.cli.main() == ERROR_UNEXPECTED

    # Test with direct call to main function
    assert cli.cli.main(["clean"] + argv) == ERROR_UNEXPECTED


def test_complete(tmp_store_dir, test_data_native_dir):
    """test complete command-line"""

    # Fill temporary store
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
    assert cli.cli.main(["add"] + argv) == SUCCESS
    assert cli.cli.main(["add"] + argv) == SUCCESS

    argv = [
        "--store-dir",
        str(tmp_store_dir),
        "--product-name",
        "myproduct",
        "--product-version",
        "2.0.0",
        str(test_data_native_dir / "dummyapp.pdb"),
    ]
    assert cli.cli.main(["add"] + argv) == SUCCESS
    assert cli.cli.main(["add"] + argv) == SUCCESS

    # Test through direct command-line when file not present yet
    with mock.patch(
        "sys.argv",
        [
            "pdbstore",
            "clean",
            "--product-name",
            "myproduct",
            "--product-version",
            "1.0.0",
            "--keep",
            "1",
        ]
        + argv[0:2],
    ):
        assert cli.cli.main() == SUCCESS

    # Test with direct call to main function when file not present yet
    assert (
        cli.cli.main(
            [
                "clean",
                "--product-name",
                "myproduct",
                "--product-version",
                "1.0.0",
                "--keep",
                "1",
            ]
            + argv[0:2]
        )
        == SUCCESS
    )
    trans = list(Store(tmp_store_dir).transactions.transactions.values())
    assert len(trans) == 3
    assert trans[0].transaction_id == "0000000003"
    assert trans[0].transaction_type == TransactionType.ADD
    assert trans[0].product == "myproduct"
    assert trans[0].version == "1.0.0"
    assert trans[1].transaction_id == "0000000004"
    assert trans[1].transaction_type == TransactionType.ADD
    assert trans[1].product == "myproduct"
    assert trans[1].version == "2.0.0"

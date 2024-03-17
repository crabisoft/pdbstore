from unittest import mock

import pytest

from pdbstore import cli
from pdbstore.cli.exit_codes import ERROR_ENCOUNTERED, ERROR_UNEXPECTED, SUCCESS
from pdbstore.config import ConfigParser
from pdbstore.store import Store
from pdbstore.typing import Generator, PathLike


@pytest.fixture(name="snapshot_store")
def fixture_snapshot_store(
    dynamic_config_object: ConfigParser, test_data_native_dir: PathLike
) -> Generator[Store, None, None]:
    """Create and fill a local snapshot Store"""

    store = Store(dynamic_config_object.get_store_directory("snapshot"))
    transaction = store.new_transaction(
        "my product",
        "1.0",
        "",
    )
    transaction.register_entry(test_data_native_dir / "dummylib.dll", False)
    transaction.register_entry(test_data_native_dir / "dummylib.pdb", False)

    store.commit(transaction, False)
    yield store


@pytest.fixture(name="snapshot_store_multi")
def fixture_snapshot_store_multi(
    dynamic_config_object: ConfigParser, test_data_native_dir: PathLike
) -> Generator[Store, None, None]:
    """Create and fill a local snapshot Store"""

    store = Store(dynamic_config_object.get_store_directory("snapshot"))
    transaction = store.new_transaction(
        "my library",
        "1.0",
        "",
    )
    transaction.register_entry(test_data_native_dir / "dummylib.dll", False)
    transaction.register_entry(test_data_native_dir / "dummylib.pdb", False)
    store.commit(transaction, False)

    transaction = store.new_transaction(
        "my app",
        "1.1",
        "Application",
    )
    transaction.register_entry(test_data_native_dir / "dummyapp.exe", False)
    transaction.register_entry(test_data_native_dir / "dummyapp.pdb", False)
    store.commit(transaction, False)

    yield store


@pytest.fixture(name="release_store")
def fixture_release_store(
    dynamic_config_object: ConfigParser,
) -> Generator[Store, None, None]:
    """Create release Store object"""

    return Store(dynamic_config_object.get_store_directory("release"))


@pytest.fixture(name="local_input_store")
def fixture_local_input_store(
    tmp_store_input: Store, test_data_native_dir
) -> Generator[Store, None, None]:
    """Create and fill a temporary Store"""

    new_transaction = tmp_store_input.new_transaction(
        "my product",
        "1.0",
        "",
    )
    new_transaction.register_entry(test_data_native_dir / "dummylib.pdb", False)
    tmp_store_input.commit(new_transaction, False)
    yield tmp_store_input


@pytest.mark.parametrize(
    "argv_and_code",
    [
        ["", ERROR_ENCOUNTERED],
        ["1", ERROR_UNEXPECTED],
        ["--store-dir", "/user/a/dir", ERROR_UNEXPECTED],
        [
            "--store-dir",
            "/user/a/dir",
            "--input-store-dir",
            "/user/b/dir",
            ERROR_UNEXPECTED,
        ],
        [
            "--store-dir",
            "/user/a/dir",
            "--input-store-dir",
            "/user/b/dir",
            "1",
            ERROR_ENCOUNTERED,
        ],
        ["--input-store-dir", "/user/b/dir", "1", ERROR_UNEXPECTED],
    ],
)
def test_incomplete(argv_and_code):
    """test empty command-line"""

    # Test through direct command-line
    with mock.patch("sys.argv", ["pdbstore", "promote"] + argv_and_code[0:-1]):
        assert cli.cli.main() == argv_and_code[-1]

    # Test with direct call to main function
    assert cli.cli.main(["promote"] + argv_and_code[0:-1]) == argv_and_code[-1]


def test_single_transaction(snapshot_store: Store, release_store: Store):
    """test complete command-line"""
    argv = [
        "--store-dir",
        str(release_store.rootdir),
        "--input-store-dir",
        str(snapshot_store.rootdir),
        "1",
    ]

    # Test through direct command-line
    with mock.patch("sys.argv", ["pdbstore", "promote"] + argv):
        assert cli.cli.main() == SUCCESS
        release_store.reset()
        assert release_store.next_transaction_id == "0000000002"
        assert len(release_store.transactions.transactions) == 1
        assert len(release_store.transactions.transactions["0000000001"].entries) == 2
        release_store.reset()

    # Test with direct call to main function

    assert cli.cli.main(["promote"] + argv) == SUCCESS
    assert release_store.next_transaction_id == "0000000003"
    release_store.reset()
    assert len(release_store.transactions.transactions) == 2
    assert len(release_store.transactions.transactions["0000000001"].entries) == 2
    assert len(release_store.transactions.transactions["0000000002"].entries) == 2


def test_multiple_transactions(snapshot_store_multi: Store, release_store: Store):
    """test complete command-line"""
    argv = [
        "--store-dir",
        str(release_store.rootdir),
        "--input-store-dir",
        str(snapshot_store_multi.rootdir),
        "1",
        "2",
    ]

    # Test through direct command-line
    with mock.patch("sys.argv", ["pdbstore", "promote"] + argv):
        assert cli.cli.main() == SUCCESS
        release_store.reset()
        assert release_store.next_transaction_id == "0000000003"
        assert len(release_store.transactions.transactions) == 2
        assert len(release_store.transactions.transactions["0000000001"].entries) == 2
        assert release_store.transactions.transactions["0000000001"].comment.startswith(
            "Promote 0000000001 from"
        )
        assert len(release_store.transactions.transactions["0000000002"].entries) == 2
        assert release_store.transactions.transactions["0000000002"].comment.startswith(
            "Application : Promote 0000000002 from"
        )
        release_store.reset()

    # Test with direct call to main function

    assert cli.cli.main(["promote"] + argv) == SUCCESS
    assert release_store.next_transaction_id == "0000000005"
    release_store.reset()
    assert len(release_store.transactions.transactions) == 4
    assert len(release_store.transactions.transactions["0000000001"].entries) == 2
    assert len(release_store.transactions.transactions["0000000002"].entries) == 2
    assert release_store.transactions.transactions["0000000001"].comment.startswith(
        "Promote 0000000001 from"
    )
    assert release_store.transactions.transactions["0000000002"].comment.startswith(
        "Application : Promote 0000000002 from"
    )
    assert len(release_store.transactions.transactions["0000000003"].entries) == 2
    assert len(release_store.transactions.transactions["0000000004"].entries) == 2
    assert release_store.transactions.transactions["0000000003"].comment.startswith(
        "Promote 0000000001 from"
    )
    assert release_store.transactions.transactions["0000000004"].comment.startswith(
        "Application : Promote 0000000002 from"
    )


def test_with_config_file(
    dynamic_config_file: PathLike, snapshot_store: Store, release_store: Store
):
    """test complete command-line"""
    argv = ["-S", "release", "-I", "snapshot", "-C", str(dynamic_config_file), "1"]

    assert len(snapshot_store.transactions.transactions) == 1

    # Test through direct command-line
    with mock.patch("sys.argv", ["pdbstore", "promote"] + argv):
        assert cli.cli.main() == SUCCESS
        release_store.reset()
        assert release_store.next_transaction_id == "0000000002"
        assert len(release_store.transactions.transactions) == 1
        assert len(release_store.transactions.transactions["0000000001"].entries) == 2
        assert release_store.transactions.transactions["0000000001"].comment.startswith(
            "Promote 0000000001 from"
        )
        release_store.reset()

    # Test with direct call to main function
    assert cli.cli.main(["promote"] + argv) == SUCCESS
    assert release_store.next_transaction_id == "0000000003"
    release_store.reset()
    assert len(release_store.transactions.transactions) == 2
    assert len(release_store.transactions.transactions["0000000001"].entries) == 2
    assert len(release_store.transactions.transactions["0000000002"].entries) == 2
    assert release_store.transactions.transactions["0000000001"].comment.startswith(
        "Promote 0000000001 from"
    )

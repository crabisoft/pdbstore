import os
import pathlib
import shutil
from unittest import mock

import pytest

from pdbstore import const, exceptions
from pdbstore.store import History, OpStatus, Store, TransactionType
from pdbstore.typing import Generator

HISTORE_FILE_EMPTY = ""
HISTORY_FILE_WITH_NEWLINE = f"firstline{os.linesep}"
HISTORY_FILE_WITHOUT_NEWLINE = "firstline"


@pytest.fixture(name="history_store")
def fixture_history_store(tmp_path, request) -> Generator[History, None, None]:
    """Generate temporary history file"""
    dsp = tmp_path / "store"
    dest = dsp / const.ADMIN_DIRNAME / const.HISTORY_FILENAME
    dest.parent.mkdir(parents=True)
    with open(dest, "wb") as hfp:
        hfp.write(bytes(request.param[0], "ascii"))
    store = History(Store(dsp))
    yield store
    shutil.rmtree(dsp)


def _assert_text_file_contents(file_path, content):
    if isinstance(content, list):
        content = (os.linesep.join(content)).encode("utf-8")
    elif isinstance(content, str):
        content = content.encode("utf-8")

    with open(file_path, "rb") as fps:
        assert fps.read() == content


@pytest.mark.parametrize("history_store", [[HISTORE_FILE_EMPTY]], indirect=True)
def test_assert_empty_history(history_store):
    """test adding new trasaction line to an empty store"""
    history_store.add("new entry")
    _assert_text_file_contents(history_store.store.history_file_path, "new entry")


@pytest.mark.parametrize("history_store", [[HISTORY_FILE_WITHOUT_NEWLINE]], indirect=True)
def test_assert_no_newline(history_store):
    """test adding new trasaction line to an empty store"""
    history_store.add("new entry")
    _assert_text_file_contents(history_store.store.history_file_path, ["firstline", "new entry"])


@pytest.mark.parametrize("history_store", [[HISTORY_FILE_WITH_NEWLINE]], indirect=True)
def test_assert_newline(history_store):
    """test adding new trasaction line to an empty store"""
    history_store.add("new entry")
    _assert_text_file_contents(history_store.store.history_file_path, ["firstline", "new entry"])


def test_commit_empty(tmp_store_dir):
    """test simple commit"""
    store = Store(tmp_store_dir)
    new_transaction = store.new_transaction(
        "my product",
        "1.0",
        "",
    )

    assert store.commit(new_transaction, False).status == OpStatus.SKIPPED


def test_commit_simple(tmp_store_dir, test_data_native_dir):
    """test simple commit"""
    store = Store(tmp_store_dir)
    new_transaction = store.new_transaction(
        "my product",
        "1.0",
        "",
    )

    new_transaction.register_entry(test_data_native_dir / "dummyapp.pdb", False)
    assert store.commit(new_transaction, False).status == OpStatus.SUCCESS


def test_commit_multiple(tmp_store_dir, test_data_native_dir):
    """test same commit multiple times"""
    store = Store(tmp_store_dir)
    new_transaction = store.new_transaction(
        "my product",
        "1.0",
        "",
    )

    new_transaction.register_entry(test_data_native_dir / "dummyapp.pdb", False)
    assert store.commit(new_transaction, False).status == OpStatus.SUCCESS
    assert store.commit(new_transaction, False).status == OpStatus.SKIPPED


def test_next_transaction_id(tmp_store_dir):
    """test transaction id generator"""
    store = Store(tmp_store_dir)
    assert store.next_transaction_id == "0000000001"

    with mock.patch("builtins.open") as _open:
        _open.side_effect = OSError("failed to read")
        with mock.patch.object(pathlib.Path, "exists") as _exists:
            _exists.return_value = True
            with pytest.raises(exceptions.ReadFileError):
                store = Store(tmp_store_dir)
                assert store.next_transaction_id


def test_fetch(tmp_store_dir, test_data_native_dir):
    """test fetch symbol"""
    store = Store(tmp_store_dir)
    new_transaction = store.new_transaction(
        "my product",
        "1.0",
        "",
    )
    new_transaction.register_entry(test_data_native_dir / "dummylib.pdb", False)

    with pytest.raises(exceptions.InvalidPEFile):
        store.fetch_symbol(test_data_native_dir / "dummylib.pdb")
    assert store.fetch_symbol(test_data_native_dir / "dummylib.dll") is None
    assert store.fetch_symbol("") is None

    assert store.commit(new_transaction, False).status == OpStatus.SUCCESS
    assert store.fetch_symbol(test_data_native_dir / "dummylib.dll") is not None


def test_find_entries(tmp_store_dir, test_data_native_dir):
    """test find entry"""
    store = Store(tmp_store_dir)
    new_transaction = store.new_transaction(
        "my product",
        "1.0",
        "",
    )
    new_transaction.register_entry(test_data_native_dir / "dummylib.pdb", False)

    assert not store.find_entries("")
    with pytest.raises(exceptions.FileNotExistsError):
        assert not store.find_entries("notfound.pdb")
    assert not store.find_entries(test_data_native_dir / "dummylib.pdb")
    assert store.commit(new_transaction, False).status == OpStatus.SUCCESS
    assert store.find_entries(test_data_native_dir / "dummylib.pdb")


def test_delete_old_versions(tmp_store, test_data_native_dir):
    """test automatic version cleanup"""
    for i in range(1, 10, 1):
        new_transaction = tmp_store.new_transaction(
            "my product",
            "1.0",
            "",
        )
        new_transaction.register_entry(test_data_native_dir / "dummylib.pdb", False)
        if i == 9:
            new_transaction.register_entry(test_data_native_dir / "dummylib.dll", False)
        assert tmp_store.commit(new_transaction, False).status == OpStatus.SUCCESS

    summary = tmp_store.remove_old_versions("my product", "1.0", 1, False)
    assert summary is not None
    assert (
        len(
            list(
                filter(
                    lambda t: not t.is_deleted(),
                    tmp_store.transactions.transactions.values(),
                )
            )
        )
        == 1
    )
    assert summary.count(True) == 8


def test_find_transaction(tmp_store: Store, test_data_native_dir):
    """test find_transaction behavior"""
    new_transaction = tmp_store.new_transaction(
        "my product",
        "1.0",
        "",
    )
    new_transaction.register_entry(test_data_native_dir / "dummylib.pdb", False)
    assert tmp_store.commit(new_transaction, False).status == OpStatus.SUCCESS
    assert tmp_store.find_transaction(1)
    with pytest.raises(exceptions.ImproperTransactionTypeError):
        assert tmp_store.find_transaction(1, TransactionType.DEL)
    with pytest.raises(exceptions.TransactionNotFoundError):
        assert tmp_store.find_transaction(2)


def test_promote_success(tmp_store_input: Store, tmp_store: Store, test_data_native_dir):
    """Test promotion with success"""
    new_transaction = tmp_store_input.new_transaction(
        "my product",
        "1.0",
        "",
    )
    new_transaction.register_entry(test_data_native_dir / "dummylib.pdb", False)
    assert tmp_store_input.commit(new_transaction, False).status == OpStatus.SUCCESS
    assert tmp_store.promote_transaction(new_transaction).status == OpStatus.SUCCESS
    assert new_transaction.is_promoted()
    assert len(tmp_store.transactions.transactions) == 1
    transaction = tmp_store.find_transaction(1, TransactionType.ADD)
    assert transaction
    assert transaction.entries
    assert transaction.entries[0].stored_path.is_file()


def test_promote_failure(tmp_store_input: Store, tmp_store: Store):
    """Test promotion with failure"""
    summary = tmp_store.promote_transaction(None)
    assert summary.status == OpStatus.FAILED
    assert summary.error_msg == "Invalid transaction object"

    new_transaction = tmp_store_input.new_transaction(
        "my product", "1.0", "", TransactionType.DEL.value
    )
    summary = tmp_store.promote_transaction(new_transaction)
    assert summary.status == OpStatus.FAILED
    assert summary.error_msg == "Invalid transaction type"

import os
import shutil

import pytest

import pdbstore
from pdbstore.store import History, OpStatus, Store

HISTORE_FILE_EMPTY = ""
HISTORY_FILE_WITH_NEWLINE = f"firstline{os.linesep}"
HISTORY_FILE_WITHOUT_NEWLINE = "firstline"


@pytest.fixture(name="history_store")
def fixture_history_store(tmp_path, request) -> History:
    """Generate temporary history file"""
    dsp = tmp_path / "store"
    dest = dsp / pdbstore.const.ADMIN_DIRNAME / pdbstore.const.HISTORY_FILENAME
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


@pytest.mark.parametrize(
    "history_store", [[HISTORY_FILE_WITHOUT_NEWLINE]], indirect=True
)
def test_assert_no_newline(history_store):
    """test adding new trasaction line to an empty store"""
    history_store.add("new entry")
    _assert_text_file_contents(
        history_store.store.history_file_path, ["firstline", "new entry"]
    )


@pytest.mark.parametrize("history_store", [[HISTORY_FILE_WITH_NEWLINE]], indirect=True)
def test_assert_newline(history_store):
    """test adding new trasaction line to an empty store"""
    history_store.add("new entry")
    _assert_text_file_contents(
        history_store.store.history_file_path, ["firstline", "new entry"]
    )


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

from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from pdbstore import exceptions
from pdbstore.store import OpStatus, Transaction, TransactionEntry, TransactionType


def test_valid(tmp_store, monkeypatch):
    """test valid transaction"""
    transaction = Transaction(tmp_store, None, TransactionType.ADD.value)
    assert transaction.id is None
    assert transaction.is_committed() is False
    assert transaction.is_delete_operation() is False
    assert transaction.is_deleted() is False
    assert transaction.is_promoted() is False

    transaction = Transaction(tmp_store, "0000000001", TransactionType.ADD.value)
    assert transaction.id == "0000000001"
    assert transaction.is_committed() is True
    assert transaction.is_delete_operation() is False
    assert transaction.is_deleted() is False
    assert transaction.is_promoted() is False

    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "exists", lambda a: False)
        assert transaction.is_deleted() is False
        assert transaction.is_promoted() is False
        mpc.setattr(Path, "exists", lambda a: True)
        assert transaction.is_deleted() is True
        assert transaction.is_promoted() is True

    transaction = Transaction(tmp_store, "0000000001", TransactionType.DEL.value)
    assert transaction.id == "0000000001"
    assert transaction.is_committed() is True
    assert transaction.is_delete_operation() is True
    assert transaction.is_deleted() is True


def test_load_entries(tmp_store):
    """test load_entries function"""
    transaction = Transaction(tmp_store, None, TransactionType.ADD.value)
    assert not transaction.entries
    transaction = Transaction(tmp_store, "0000000001", TransactionType.ADD.value)
    assert not transaction.entries


def test_invalid(tmp_store):
    """test invalid transaction type"""
    with pytest.raises(exceptions.PDBStoreException):
        Transaction(tmp_store, None, "badtype")


def test_register_entry(tmp_store, test_data_native_dir):
    """test invalid transaction type"""
    transaction = Transaction(tmp_store, None, TransactionType.ADD.value)
    with pytest.raises(exceptions.FileNotExistsError):
        assert transaction.register_entry("notfound-file", False) is False
    assert transaction.register_entry(None, False) is False
    assert transaction.register_entry(test_data_native_dir / "dummyapp.pdb", False) is True


def test_deleted(tmp_store, monkeypatch, capsys):
    """test deleted tag"""
    transaction = Transaction(tmp_store, "0000000001", TransactionType.ADD.value)
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "is_file", lambda a: False)
        transaction.mark_deleted()
        assert "file not found, so not possible to mark it as deleted" in capsys.readouterr().err
        mpc.setattr(Path, "is_file", lambda a: True)
        with mock.patch("os.rename", return_value=True) as ren_mock:
            transaction.mark_deleted()
            ren_mock.assert_called()


def test_promoted(tmp_store, monkeypatch, capsys):
    """test promoted tag"""
    transaction = Transaction(tmp_store, "0000000001", TransactionType.ADD.value)
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "is_file", lambda a: False)
        transaction.mark_promoted()
        assert "file not found, so not possible to mark it as promoted" in capsys.readouterr().err
        mpc.setattr(Path, "is_file", lambda a: True)
        with mock.patch("shutil.copyfile", return_value=True) as ren_mock:
            transaction.mark_promoted()
            ren_mock.assert_called()


def test_representation(tmp_store):
    """test transaction representation"""
    transaction = Transaction(
        tmp_store,
        "0000000001",
        TransactionType.ADD.value,
        "file",
        datetime.utcfromtimestamp(1699195604),
    )
    assert str(transaction) == '0000000001,add,file,11/05/2023,14:46:44,"None","None","None",'
    assert repr(transaction) == '0000000001,add,file,11/05/2023,14:46:44,"None","None","None",'

    transaction = Transaction(
        tmp_store,
        None,
        TransactionType.ADD.value,
        "file",
        datetime.fromtimestamp(1699195604),
    )
    assert str(transaction) == ""
    assert repr(transaction) == ""

    transaction = Transaction(tmp_store, "0000000001", TransactionType.ADD.value)
    assert str(transaction) == ""
    assert repr(transaction) == ""

    transaction = Transaction(
        tmp_store, "0000000002", TransactionType.DEL.value, deleted_id="0000000001"
    )
    assert str(transaction) == "0000000002,del,0000000001"
    transaction = Transaction(tmp_store, "0000000002", TransactionType.DEL.value)
    assert str(transaction) == ""


def test_parallel_commit(tmp_store, test_data_native_dir):
    """test commit transactions in parallel"""
    transaction = Transaction(
        tmp_store,
        None,
        TransactionType.ADD.value,
        "file",
        datetime.utcfromtimestamp(1699195604),
    )
    # Existing file
    transaction.add_entry(
        TransactionEntry(
            tmp_store,
            "dummyapp.pdb",
            "DBF7CE25C6DC4E0EA9AD889187E296A21",
            test_data_native_dir / "dummyapp.pdb",
            False,
        )
    )
    # Non-existent file
    transaction.add_entry(
        TransactionEntry(
            tmp_store,
            "a-notfound.pdb",
            "DBF7CE25C6DC4E0EA9AD889187E296A21",
            test_data_native_dir / "a-notfound.pdb",
            False,
        )
    )

    summary = transaction.commit("0000000010", datetime.now(), False)
    assert summary.count(True) == 0
    assert summary.count(False) == 1
    files = sorted(summary.files, key=lambda f: f["path"])
    assert len(files) == 2
    assert files[0]["status"] == OpStatus.FAILED.value
    assert files[1]["status"] == OpStatus.SUCCESS.value
    assert transaction.compute_disk_usage() > 0
    assert transaction.find_entry("", "") is None
    assert transaction.find_entry("dummyapp.pdb", "DBF7CE25C6DC4E0EA9AD889187E296A21") is not None
    assert transaction.find_entry("dummyapp.pdb", "") is None


def test_parse_line(tmp_store):
    """Test parse_line behavior"""
    assert (
        Transaction.parse_line(
            tmp_store, '0000000001,add,file,11/05/2023,14:46:44,"None","None","None",'
        )
        is not None
    )
    assert Transaction.parse_line(tmp_store, "0000000001,add,") is None
    assert Transaction.parse_line(tmp_store, "0000000002,del,0000000001") is not None
    assert Transaction.parse_line(tmp_store, "0000000002,del,") is None
    assert Transaction.parse_line(tmp_store, "0000000002,delc,0000000001") is None

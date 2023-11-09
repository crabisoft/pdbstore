from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from pdbstore import exceptions
from pdbstore.store import Transaction, TransactionType


def test_valid(tmp_store, monkeypatch):
    """test valid transaction"""
    transaction = Transaction(tmp_store, None, TransactionType.ADD.value)
    assert transaction.id is None
    assert transaction.is_committed() is False
    assert transaction.is_delete_operation() is False
    assert transaction.is_deleted() is False

    transaction = Transaction(tmp_store, "0000000001", TransactionType.ADD.value)
    assert transaction.id == "0000000001"
    assert transaction.is_committed() is True
    assert transaction.is_delete_operation() is False
    assert transaction.is_deleted() is False

    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "exists", lambda a: False)
        assert transaction.is_deleted() is False
        mpc.setattr(Path, "exists", lambda a: True)
        assert transaction.is_deleted() is True

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
    assert (
        transaction.register_entry(test_data_native_dir / "dummyapp.pdb", False) is True
    )


def test_deleted(tmp_store, monkeypatch, capsys):
    """test deleted tag"""
    transaction = Transaction(tmp_store, "0000000001", TransactionType.ADD.value)
    with monkeypatch.context() as mpc:
        mpc.setattr(Path, "is_file", lambda a: False)
        transaction.mark_deleted()
        assert (
            "file not found, so not possible to mark it as deleted"
            in capsys.readouterr().err
        )
        mpc.setattr(Path, "is_file", lambda a: True)
        with mock.patch("os.rename", return_value=True) as ren_mock:
            transaction.mark_deleted()
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
    assert (
        str(transaction)
        == '0000000001,add,file,11/05/2023,14:46:44,"None","None","None",'
    )
    assert (
        repr(transaction)
        == '0000000001,add,file,11/05/2023,14:46:44,"None","None","None",'
    )

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

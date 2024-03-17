import importlib
import os
from pathlib import Path
from unittest import mock

import pytest

import pdbstore
from pdbstore import exceptions
from pdbstore.store import TransactionEntry


def test_valid(tmp_store, test_data_native_dir):
    """test valid transaction entry"""
    entry = TransactionEntry(
        tmp_store,
        "dummylib.pdb",
        "1972BE39B97341928816018A8ECD08D91",
        test_data_native_dir / "dummylib.pdb",
        False,
    )
    assert entry.file_path == test_data_native_dir / "dummylib.pdb"
    assert (
        entry.stored_path
        == tmp_store.rootdir / "dummylib.pdb" / "1972BE39B97341928816018A8ECD08D91" / "dummylib.pdb"
    )
    assert (
        entry.rel_path
        == Path("dummylib.pdb") / "1972BE39B97341928816018A8ECD08D91" / "dummylib.pdb"
    )
    assert entry.is_committed() is False
    assert entry.is_compressed() is False

    entry = TransactionEntry(
        tmp_store,
        "dummylib.pdb",
        "1972BE39B97341928816018A8ECD08D91",
        test_data_native_dir / "dummylib.pdb",
        True,
    )
    assert entry.file_path == test_data_native_dir / "dummylib.pdb"
    assert (
        entry.stored_path
        == tmp_store.rootdir / "dummylib.pdb" / "1972BE39B97341928816018A8ECD08D91" / "dummylib.pd_"
    )
    assert (
        entry.rel_path
        == Path("dummylib.pdb") / "1972BE39B97341928816018A8ECD08D91" / "dummylib.pd_"
    )
    assert entry.is_committed() is False
    assert entry.is_compressed() is True


def test_commit_success(tmp_store, test_data_native_dir):
    """test commit transaction with success"""
    entry = TransactionEntry(
        tmp_store,
        "dummylib.pdb",
        "1972BE39B97341928816018A8ECD08D91",
        test_data_native_dir / "dummylib.pdb",
        False,
    )
    assert entry.commit() is True
    assert entry.commit() is False
    assert entry.commit(True) is True


def test_commit_failure(tmp_store, test_data_native_dir):
    """test commit transaction with failure"""
    entry = TransactionEntry(
        tmp_store,
        "dummylib.pdb",
        "1972BE39B97341928816018A8ECD08D91",
        test_data_native_dir / "notfound.pdb",
        False,
    )
    with pytest.raises(exceptions.CopyFileError):
        entry.commit()


def test_creation_success(tmp_store, test_data_native_dir):
    """test static entry creation with success"""
    entry = TransactionEntry.create(tmp_store, test_data_native_dir / "dummylib.pdb")
    assert entry is not None
    assert entry.file_path == test_data_native_dir / "dummylib.pdb"
    assert (
        entry.stored_path
        == tmp_store.rootdir / "dummylib.pdb" / "1972BE39B97341928816018A8ECD08D91" / "dummylib.pdb"
    )
    assert entry.is_committed() is False
    assert entry.is_compressed() is False


def test_creation_failure(tmp_store, test_data_native_dir):
    """test static entry creation with failure"""
    with pytest.raises(exceptions.FileNotExistsError):
        entry = TransactionEntry.create(tmp_store, test_data_native_dir / "notfound.pdb")
    entry = TransactionEntry.create(tmp_store, "")
    assert entry is None


def test_extract_success(tmp_path, tmp_store, test_data_native_dir, fake_process):
    """test commit transaction with success"""
    entry = TransactionEntry.create(tmp_store, test_data_native_dir / "dummylib.pdb")
    assert entry is not None
    assert entry.commit() is True
    assert entry.extract(tmp_path) == os.path.join(tmp_path, "dummylib.pdb")

    entry.compressed = True
    fake_process.register(
        ["gcab", "-z", "-n", "-c", entry.stored_path, entry.file_path],
        stdout=b"compression ok",
        returncode=0,
    )
    fake_process.register(
        ["gcab", "-x", "-C", tmp_path, entry.stored_path],
        stdout=b"decompression ok",
        returncode=0,
    )

    with mock.patch("pdbstore.util.which") as _which:
        _which.return_value = "/usr/bin/gcab"
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.is_decompression_supported() is True
        assert entry.commit() is True
        assert entry.extract(tmp_path) == os.path.join(tmp_path, "dummylib.pdb")

        pdbstore.io.cab.decompress = None
        assert pdbstore.io.is_decompression_supported() is False
        with pytest.raises(exceptions.DecompressionNotSupportedError):
            entry.extract(tmp_path)


def test_extract_failure(tmp_path, tmp_store, test_data_native_dir, fake_process):
    """test commit transaction with success"""
    entry = TransactionEntry(
        tmp_store,
        "notfound.pdb",
        "1972BE39B97341928816018A8ECD08D91",
        test_data_native_dir / "notfound.pdb",
        False,
    )
    with pytest.raises(exceptions.CopyFileError):
        entry.commit()

    entry = TransactionEntry.create(tmp_store, test_data_native_dir / "dummylib.pdb")
    entry.compressed = True
    fake_process.register(
        ["gcab", "-z", "-n", "-c", entry.stored_path, entry.file_path],
        stdout=b"compression ok",
        returncode=0,
    )
    fake_process.register(
        ["gcab", "-x", "-C", tmp_path, entry.stored_path],
        stdout=b"decompression failed",
        returncode=1,
    )

    with mock.patch("pdbstore.util.which") as _which:
        _which.return_value = "/usr/bin/gcab"
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.is_decompression_supported() is True
        assert entry.commit() is True
        with pytest.raises(exceptions.CabCompressionError):
            entry.extract(tmp_path)

        pdbstore.io.cab.decompress = None
        assert pdbstore.io.is_decompression_supported() is False
        with pytest.raises(exceptions.DecompressionNotSupportedError):
            entry.extract(tmp_path)

    with mock.patch("shutil.copy") as _copy:
        _copy.side_effect = OSError("failed to copy")
        entry.compressed = False
        with pytest.raises(exceptions.CopyFileError):
            entry.extract(tmp_path)


def test_large_compressed_file(tmp_store, test_data_native_dir):
    """test no compress for very large file"""
    with mock.patch("pdbstore.io.file.get_file_size") as _get_file_size:
        _get_file_size.return_value = TransactionEntry.MAX_COMPRESSED_FILE_SIZE + 10
        entry = TransactionEntry(
            tmp_store,
            "dummylib.pdb",
            "1972BE39B97341928816018A8ECD08D91",
            test_data_native_dir / "dummylib.pdb",
            True,
        )
        assert entry.commit() is True
        assert entry.is_compressed() is False
        assert entry.stored_path.exists()

import io
import pathlib
from unittest import mock

import pytest

from pdbstore import exceptions
from pdbstore.io import file


@pytest.mark.parametrize(
    "file_info",
    [("dummyapp.exe", "B85047B88000"), ("dummylib.dll", "F2B0D7208000")],
)
def test_hash_pe_native(test_data_native_dir, file_info):
    """Test executable file hash"""
    hash_key = file.compute_hash_key(test_data_native_dir / file_info[0])
    assert hash_key == file_info[1]


@pytest.mark.parametrize(
    "file_info",
    [
        ("dummyapp.pdb", "DBF7CE25C6DC4E0EA9AD889187E296A21"),
        ("dummylib.pdb", "1972BE39B97341928816018A8ECD08D91"),
    ],
)
def test_hash_pdb_native(test_data_native_dir, file_info):
    """Test PDB file hash"""
    hash_key = file.compute_hash_key(test_data_native_dir / file_info[0])
    assert hash_key == file_info[1]


@pytest.mark.parametrize(
    "file_info",
    [
        ("dummylib.pdb", "26AAE66BC7ED4655BD38492E7BB268831"),
    ],
)
def test_hash_pdb_portable(test_data_portable_dir, file_info):
    """Test PDB file hash"""
    hash_key = file.compute_hash_key(test_data_portable_dir / file_info[0])
    assert hash_key == file_info[1]


def test_hash_invalid(test_data_invalid_dir):
    """Test invalid exe file"""
    with pytest.raises(exceptions.UnknowFileTypeError):
        file.compute_hash_key(test_data_invalid_dir / "bad.exe")


def test_hash_not_found(test_data_dir):
    """Test inexistant file"""
    with pytest.raises(exceptions.FileNotExistsError):
        file.compute_hash_key(test_data_dir / "notfound.pdb")


@pytest.mark.parametrize(
    "dir_name",
    [
        "test_data_native_dir",
        "test_data_portable_dir",
    ],
)
def test_incomplete(dir_name, request):
    """test incomplete PDB file content"""
    base_dir = request.getfixturevalue(dir_name)
    pdb_path = base_dir / "dummylib.pdb"
    with open(pdb_path, "rb") as fps:
        fds = io.BytesIO(fps.read(2))
        fps.seek(0)
        fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))

        with mock.patch.object(pathlib.Path, "open") as mocked:
            mocked.return_value = fds
            with pytest.raises(exceptions.UnknowFileTypeError):
                file.compute_hash_key(pdb_path)

        fds = io.BytesIO(fps.read(60))
        fps.seek(0)
        fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))
        with mock.patch.object(pathlib.Path, "open") as mocked:
            mocked.return_value = fds
            with pytest.raises(exceptions.UnknowFileTypeError):
                file.compute_hash_key(pdb_path)

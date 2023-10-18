import pytest

from pdbstore import exceptions
from pdbstore.io import file


@pytest.mark.parametrize(
    "file_info",
    [("dummyapp.exe", "B85047B88000"), ("dummylib.dll", "F2B0D7208000")],
)
def test_hash_pe(test_data_dir, file_info):
    """Test executable file hash"""
    hash_key = file.compute_hash_key(test_data_dir / file_info[0])
    assert hash_key == file_info[1]


@pytest.mark.parametrize(
    "file_info",
    [
        ("dummyapp.pdb", "DBF7CE25C6DC4E0EA9AD889187E296A21"),
        ("dummylib.pdb", "1972BE39B97341928816018A8ECD08D91"),
    ],
)
def test_hash_pdb(test_data_dir, file_info):
    """Test PDB file hash"""
    hash_key = file.compute_hash_key(test_data_dir / file_info[0])
    assert hash_key == file_info[1]


def test_hash_invalid(test_data_dir):
    """Test invalid exe file"""
    with pytest.raises(exceptions.UnknowFileTypeError):
        file.compute_hash_key(test_data_dir / "invalid.exe")


def test_hash_not_found(test_data_dir):
    """Test inexistant file"""
    with pytest.raises(exceptions.FileNotExistsError):
        file.compute_hash_key(test_data_dir / "notfound.pdb")

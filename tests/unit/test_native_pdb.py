import io
import pathlib
from unittest import mock

import pytest

from pdbstore import exceptions
from pdbstore.io import pdbfile


@pytest.mark.parametrize(
    "file_info",
    [
        ("dummyapp.pdb", "DBF7CE25C6DC4E0EA9AD889187E296A2", "1"),
        ("dummylib.pdb", "1972BE39B97341928816018A8ECD08D9", "1"),
    ],
)
def test_native(test_data_native_dir, file_info):
    """Test PDB file hash"""
    pdb = pdbfile.PDB(test_data_native_dir / file_info[0])
    assert f"{pdb.guid}".upper() == file_info[1]
    assert f"{pdb.age or ''}".upper() == file_info[2]


def test_incomplete(test_data_native_dir):
    """test incomplete PDB file content"""
    pdb_path = test_data_native_dir / "dummyapp.pdb"
    with open(pdb_path, "rb") as fps:
        fds = io.BytesIO(fps.read(5))
        fps.seek(0)
        fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))

        with mock.patch.object(pathlib.Path, "open") as mocked:
            mocked.return_value = fds
            with pytest.raises(exceptions.PDBSignatureNotFoundError):
                pdbfile.PDB(pdb_path)

        fds = io.BytesIO(fps.read(60))
        fps.seek(0)
        fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))

        with mock.patch.object(pathlib.Path, "open") as mocked:
            mocked.return_value = fds
            with pytest.raises(exceptions.ParseFileError):
                pdbfile.PDB(pdb_path)


def test_exe(test_data_native_dir):
    """Test invalid pdb file"""
    with pytest.raises(exceptions.PDBSignatureNotFoundError):
        pdbfile.PDB(test_data_native_dir / "dummyapp.exe")


def test_pdb_not_found(test_data_dir):
    """Test inexistant file"""
    with pytest.raises(exceptions.FileNotExistsError):
        pdbfile.PDB(test_data_dir / "notfound.pdb")

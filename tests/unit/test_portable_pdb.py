import io
import pathlib
from unittest import mock

import pytest

from pdbstore import exceptions
from pdbstore.io import portablepdbfile


@pytest.mark.parametrize(
    "file_info",
    [
        ("dummylib.pdb", "26AAE66BC7ED4655BD38492E7BB26883", "1"),
    ],
)
def test_native(test_data_portable_dir, file_info):
    """Test portable PDB file hash"""
    pdb = portablepdbfile.PortablePDB(test_data_portable_dir / file_info[0])
    assert f"{pdb.guid}".upper() == file_info[1]
    assert f"{pdb.age or ''}".upper() == file_info[2]


def test_incomplete(test_data_portable_dir):
    """test incomplete portable PDB file content"""
    pdb_path = test_data_portable_dir / "dummylib.pdb"
    with open(pdb_path, "rb") as fps:
        fds = io.BytesIO(fps.read(2))
        fps.seek(0)
        fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))

        with mock.patch.object(pathlib.Path, "open") as mocked:
            mocked.return_value = fds
            with pytest.raises(exceptions.PDBSignatureNotFoundError):
                portablepdbfile.PortablePDB(pdb_path)

        fds = io.BytesIO(fps.read(60))
        fps.seek(0)
        fds.close = mock.Mock(return_value=None, side_effect=lambda: fds.seek(0))

        with mock.patch.object(pathlib.Path, "open") as mocked:
            mocked.return_value = fds
            with pytest.raises(exceptions.ParseFileError):
                portablepdbfile.PortablePDB(pdb_path)


def test_pdb_not_found(test_data_dir):
    """Test inexistant file"""
    with pytest.raises(exceptions.FileNotExistsError):
        portablepdbfile.PortablePDB(test_data_dir / "notfound.pdb")

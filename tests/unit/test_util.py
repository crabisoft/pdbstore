import os
import shutil
import sys
from pathlib import Path

import pytest

from pdbstore import util


@pytest.fixture(name="local_exe")
def fixture_local_exe(tmp_path):
    """Copy temporarely current python executable into a temporary directory"""
    python_exe = sys.executable
    python_tmp_exe: Path = tmp_path / "util" / (os.path.basename(sys.executable))
    python_tmp_exe.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(python_exe, python_tmp_exe)
    shutil.copymode(python_exe, python_tmp_exe)
    yield python_tmp_exe
    python_tmp_exe.unlink(missing_ok=True)


def test_without_env():
    """test with default logic"""
    python_exe = os.path.basename(sys.executable)
    assert util.which(python_exe) == sys.executable


def test_with_env(monkeypatch, local_exe):
    """test using an environment variable"""
    python_exe = os.path.basename(sys.executable)
    with monkeypatch.context() as mpc:
        mpc.setenv("CUSTOM_EXE_DIR", os.path.dirname(local_exe))
        assert util.which(python_exe, "CUSTOM_EXE_DIR") == os.fspath(local_exe)


def test_from_str():
    """test String to Path conversion"""
    assert util.str_to_path(None) is None
    assert util.str_to_path("") is None
    assert util.str_to_path(sys.executable) == Path(sys.executable)


def test_to_str():
    """test Path to String conversion"""
    assert util.path_to_str(None) is None
    assert util.path_to_str("") is None
    assert util.path_to_str(Path(sys.executable)) == sys.executable


@pytest.mark.parametrize(
    "param",
    [
        ["/home/johndoe/documents/readme.txt", 9, "readme.txt"],
        ["/home/johndoe/documents/readme.txt", 18, "/.../readme.txt"],
        ["/home/johndoe/documents/readme.txt", 26, "/.../documents/readme.txt"],
        ["/home/johndoe/documents/readme.txt", 32, "/home/.../documents/readme.txt"],
        [
            "/home/johndoe/documents/readme.txt",
            40,
            "/home/johndoe/documents/readme.txt",
        ],
        ["c:\\Users\\JohnDoe\\Documents\\readme.txt", 9, "readme.txt"],
        ["c:\\Users\\JohnDoe\\Documents\\readme.txt", 18, "c:\\...\\readme.txt"],
        ["c:\\Users\\JohnDoe\\Documents\\readme.txt", 26, "c:\\...\\readme.txt"],
        [
            "c:\\Users\\JohnDoe\\Documents\\readme.txt",
            32,
            "c:\\...\\Documents\\readme.txt",
        ],
        [
            "c:\\Users\\JohnDoe\\Documents\\readme.txt",
            40,
            "c:\\Users\\JohnDoe\\Documents\\readme.txt",
        ],
    ],
)
def test_abbreviate(param):
    """test abbreviate function"""
    assert util.abbreviate(param[0], param[1]) == param[2]

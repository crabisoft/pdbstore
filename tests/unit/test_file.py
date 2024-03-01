import time
from pathlib import Path

import pytest

from pdbstore.exceptions import ReadFileError
from pdbstore.io import file
from pdbstore.typing import Generator

NEWLINES_FILE_CONTENT = "first line\nsecond line"

TEXT_FILE_WITH_LF = "first line\nsecond line"
TEXT_FILE_WITH_CRLF = "first line\r\nsecond line"


@pytest.fixture(name="file_access")
def fixture_file_access(tmp_path, request) -> Generator[Path, None, None]:
    """Generate temporary history file"""
    dest = tmp_path / f"file-{time.time()}.bin"
    with open(dest, "wb") as hfp:
        hfp.write(bytes(request.param[0], "ascii"))
    yield dest
    dest.unlink(missing_ok=True)


def test_file_binary_not_found(tmp_path):
    """test binary file which doesn't exists"""
    file_path = tmp_path / "nbin"
    with pytest.raises(ReadFileError) as excinfo:
        file.read_binary_file(file_path)
    assert str(file_path) in str(excinfo.value)


def read_text_file_not_found(tmp_path):
    """test text file which doesn't exists"""
    file_path = tmp_path / "ntxt"
    with pytest.raises(ReadFileError) as excinfo:
        file.read_text_file(file_path)
    assert str(file_path) in str(excinfo.value)
    with pytest.raises(ReadFileError) as excinfo:
        file.read_text_file(file_path, True)
    assert str(file_path) in str(excinfo.value)


def test_dir_binary(tmp_path):
    """test binary file with directory path"""
    dir_path = tmp_path / "bin"
    dir_path.mkdir()
    with pytest.raises(ReadFileError) as excinfo:
        file.read_binary_file(dir_path)
    assert str(dir_path) in str(excinfo.value)


def test_dir_text(tmp_path):
    """test text file with directory path"""
    dir_path = tmp_path / "txt"
    dir_path.mkdir()
    with pytest.raises(ReadFileError) as excinfo:
        file.read_text_file(dir_path)
    assert str(dir_path) in str(excinfo.value)


@pytest.mark.parametrize("file_access", [[TEXT_FILE_WITH_LF]], indirect=True)
def test_binary_file_without_split(file_access):
    """test binary file"""
    content = file.read_binary_file(file_access)
    assert content == NEWLINES_FILE_CONTENT.encode("utf-8")


@pytest.mark.parametrize("file_access", [[TEXT_FILE_WITH_LF]], indirect=True)
def test_text_file_with_split_unix(file_access):
    """test unix text file with multiple lines"""
    content = file.read_text_file(file_access)
    assert content == NEWLINES_FILE_CONTENT

    content = file.read_text_file(file_access, True)
    assert content == NEWLINES_FILE_CONTENT.split("\n")


@pytest.mark.parametrize("file_access", [[TEXT_FILE_WITH_CRLF]], indirect=True)
def test_text_file_with_split_windows(file_access):
    """test windows text file with multiple lines"""
    content = file.read_text_file(file_access)
    assert content == NEWLINES_FILE_CONTENT

    content = file.read_text_file(file_access, True)
    assert content == NEWLINES_FILE_CONTENT.split("\n")


@pytest.mark.parametrize("file_access", [[TEXT_FILE_WITH_CRLF]], indirect=True)
def test_valid_file_size(file_access):
    """test valid file size behavior"""
    assert file.get_file_size(file_access) > 0


@pytest.mark.parametrize(
    "file_path",
    [None, "", "/invalid/path"],
)
def test_invalid_file_size(file_path):
    """test invalid file size behavior"""
    assert file.get_file_size(file_path) == 0

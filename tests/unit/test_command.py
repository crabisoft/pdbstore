import os
from pathlib import Path

import pytest

from pdbstore.io.file import build_files_list


@pytest.fixture(name="response_file")
def fixture_response_file(tmp_path, test_data_native_dir):
    """Generate temporary responsive file to validate build_files_list api"""
    response_path: Path = tmp_path / "response.rsp"
    with response_path.open("wt", encoding="utf-8") as rpf:
        for root, _, filenames in os.walk(test_data_native_dir):
            for filename in filenames:
                rpf.write(f"{os.path.join(root, filename)}\n")
            break
        rpf.write(f"{test_data_native_dir / 'history'}\n")
    yield response_path
    response_path.unlink(missing_ok=True)


def test_build_list_empty():
    """test build_files_list with empty list"""
    assert not build_files_list([])


def test_build_list_non_existent():
    """test build_files_list with an non-existent file"""
    assert not build_files_list(["/one/directory/file.notfound"], exist_only=True)
    assert build_files_list(["/one/directory/file.notfound"], exist_only=False) == [
        Path("/one/directory/file.notfound")
    ]
    assert not build_files_list("/one/directory/file.notfound", exist_only=True)
    assert build_files_list("/one/directory/file.notfound", exist_only=False) == [
        Path("/one/directory/file.notfound")
    ]


def test_build_list_one(test_data_native_dir):
    """test build_files_list with only one file path"""
    test_path: Path = test_data_native_dir / "dummyapp.pdb"
    assert build_files_list([test_path]) == [test_path]
    assert build_files_list([str(test_path)]) == [test_path]


def test_build_list_recursive(test_data_dir):
    """test build_files_list with one directory and recursive option"""
    build_list = build_files_list([test_data_dir], recursive=True)
    assert len(build_list) == 7


def test_build_list_response(response_file):
    """test build_files_list with a response file"""
    build_list = build_files_list(f"@{response_file}", recursive=True)
    assert len(build_list) == 5

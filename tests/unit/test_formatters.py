import pytest

from pdbstore import exceptions
from pdbstore.cli import formatters
from pdbstore.store import OpStatus, Summary, TransactionType


def test_default_json(capsys):
    """test default json formatter"""
    formatters.default_json_formatter({})
    assert (
        capsys.readouterr().out
        == """{}
"""
    )

    formatters.default_json_formatter({"key": "value", "second": "val"})
    assert (
        capsys.readouterr().out
        == """{
    "key": "value",
    "second": "val"
}
"""
    )


def test_summary_json(capsys):
    """test summary object json formatter"""
    formatters.summary_json_formatter(Summary())
    assert (
        capsys.readouterr().out
        == """[
    {
        "id": null,
        "type": "undefined",
        "status": "success",
        "success": 0,
        "failure": 0,
        "skip": 0,
        "files": [],
        "message": null
    }
]
"""
    )
    summary = Summary("0000000014", OpStatus.SUCCESS, TransactionType.ADD, "error_msg", 0)
    formatters.summary_json_formatter(summary)
    assert (
        capsys.readouterr().out
        == """[
    {
        "id": "0000000014",
        "type": "add",
        "status": "success",
        "success": 0,
        "failure": 0,
        "skip": 0,
        "files": [],
        "message": "error_msg"
    }
]
"""
    )
    summary = Summary("0000000014", OpStatus.SUCCESS, TransactionType.ADD, None, 0)
    summary.add_file("input.pdb", OpStatus.FAILED, "file not found")
    with pytest.raises(exceptions.PDBAbortExecution):
        formatters.summary_json_formatter(summary)
    assert (
        capsys.readouterr().out
        == """[
    {
        "id": "0000000014",
        "type": "add",
        "status": "success",
        "success": 0,
        "failure": 1,
        "skip": 0,
        "files": [
            {
                "path": "input.pdb",
                "status": "fail",
                "error": "file not found"
            }
        ],
        "message": null
    }
]
"""
    )

    summary = Summary("0000000014", OpStatus.SUCCESS, TransactionType.DEL, None, 0)
    summary.add_file("input.pdb", OpStatus.SKIPPED, "file not found")
    formatters.summary_json_formatter(summary)
    assert (
        capsys.readouterr().out
        == """[
    {
        "id": "0000000014",
        "type": "del",
        "status": "success",
        "success": 0,
        "failure": 0,
        "skip": 1,
        "files": [
            {
                "path": "input.pdb",
                "status": "skip",
                "error": "file not found"
            }
        ],
        "message": null
    }
]
"""
    )
    summary.linked = Summary("0000000015", OpStatus.SUCCESS, TransactionType.DEL, None, 0)
    summary.linked.add_file("input.pdb", OpStatus.SKIPPED, "file not found")
    formatters.summary_json_formatter(summary)
    assert (
        capsys.readouterr().out
        == """[
    {
        "id": "0000000014",
        "type": "del",
        "status": "success",
        "success": 0,
        "failure": 0,
        "skip": 2,
        "files": [
            {
                "path": "input.pdb",
                "status": "skip",
                "error": "file not found"
            }
        ],
        "message": null
    },
    {
        "id": "0000000015",
        "type": "del",
        "status": "success",
        "success": 0,
        "failure": 0,
        "skip": 1,
        "files": [
            {
                "path": "input.pdb",
                "status": "skip",
                "error": "file not found"
            }
        ],
        "message": null
    }
]
"""
    )

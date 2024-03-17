import subprocess
import sys
from pathlib import Path
from unittest import mock

import pdbstore
from pdbstore import __main__  # noqa: F401
from pdbstore.cli.exit_codes import (
    ERROR_COMMAND_NAME,
    ERROR_ENCOUNTERED,
    ERROR_INVALID_CONFIGURATION,
    ERROR_SUBCOMMAND_NAME,
    SUCCESS,
)
from pdbstore.io.output import PDBStoreOutput


def test_version(capsys):
    """test --version command-line"""

    # Test through direct command-line when file not present yet
    with mock.patch("sys.argv", ["pdbstore", "--version"]):
        assert pdbstore.cli.cli.main() == SUCCESS
        assert capsys.readouterr().out == f"{pdbstore.__version__}\n"
    assert pdbstore.cli.cli.main(["--version"]) == 0
    assert capsys.readouterr().out == f"{pdbstore.__version__}\n"


def test_config_error(capsys):
    """test --version command-line"""
    assert (
        pdbstore.cli.cli.main(
            [
                "add",
                "--store",
                "notfound",
                "-p",
                "myproduct",
                "-v",
                "1.0.0",
                "notfound.pdb",
            ]
        )
        == ERROR_INVALID_CONFIGURATION
    )
    assert (
        "Symbol store id was provided (notfound) but no config file found"
        in capsys.readouterr().err
    )

    assert pdbstore.cli.cli.main(["--help", "--store", "notfound"]) == SUCCESS
    assert "Storage commands" in capsys.readouterr().out

    with mock.patch("sys.argv", ["pdbstore", "--store", "notfound"]):
        assert pdbstore.cli.cli.main() == ERROR_COMMAND_NAME
        assert (
            "'--store' is not a PDBStore command. See 'pdbstore --help'" in capsys.readouterr().err
        )

    with mock.patch("sys.argv", ["pdbstore", "add", "--store", "notfound"]):
        assert pdbstore.cli.cli.main() == ERROR_INVALID_CONFIGURATION
        assert (
            "Symbol store id was provided (notfound) but no config file found"
            in capsys.readouterr().err
        )

    with mock.patch("sys.argv", ["pdbstore", "--help", "--store", "notfound"]):
        assert pdbstore.cli.cli.main() == SUCCESS
        assert "Storage commands" in capsys.readouterr().out


def test_log_file(tmp_path):
    """test -L/--log-file command-line"""
    log_file_path: Path = tmp_path / "test_cli.log"
    assert pdbstore.cli.cli.main(["add", "--log-file", str(log_file_path), "--help"]) == SUCCESS
    PDBStoreOutput.define_log_output(None)
    assert log_file_path.exists() is True


def test_more_than_once(capsys):
    """test multiple -S/--store command-line"""
    assert (
        pdbstore.cli.cli.main(["add", "--store", "store1", "--store", "store2"])
        == ERROR_ENCOUNTERED
    )
    assert "pdbstore add: error: --store can only be specified once" in capsys.readouterr().err


def test_similar_name(capsys):
    """test result of print similar message"""
    assert pdbstore.cli.cli.main(["a"]) == ERROR_COMMAND_NAME
    assert capsys.readouterr().err.startswith(
        "'a' is not a PDBStore command. See 'pdbstore --help'."
    )

    assert pdbstore.cli.cli.main(["ad"]) == ERROR_COMMAND_NAME
    assert (
        capsys.readouterr().err
        == """'ad' is not a PDBStore command. See 'pdbstore --help'.

The most similar command is
    add

"""
    )


def test_no_subcommand_name(capsys):
    """test command without subcommand name"""
    assert pdbstore.cli.cli.main(["report"]) == ERROR_SUBCOMMAND_NAME
    out, err = capsys.readouterr()
    assert out.startswith("usage: pdbstore report {file,product,transaction")
    assert err == ""


def test_unsupported_subcommand_name(capsys):
    """test command with unsupported subcommand name"""
    assert pdbstore.cli.cli.main(["report", "invalid"]) == ERROR_SUBCOMMAND_NAME
    out, err = capsys.readouterr()
    assert out.startswith("usage: pdbstore report {file,product,transaction")
    assert err == ""


def test_commandline_as_module():
    """test command-line invoked as python module"""

    command = [sys.executable, "-m", "pdbstore", "--version"]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        stdout, stderr = proc.communicate()
        assert proc.returncode == 0
        assert stdout.decode().startswith(pdbstore.__version__)
        assert stderr.decode() == ""

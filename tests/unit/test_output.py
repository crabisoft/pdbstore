import sys
from importlib import reload
from unittest import mock

import pytest
from colorama import Fore, Style

from pdbstore import const, exceptions
from pdbstore.io import output


def test_color_schem(monkeypatch):
    """test color scheme"""
    with monkeypatch.context() as mpc:
        mpc.delenv(const.ENV_PDBSTORE_COLOR_DARK, False)
        reload(output)
        assert output.Color.RED == Fore.RED
        assert output.Color.WHITE == Fore.WHITE
        assert output.Color.CYAN == Fore.CYAN
        assert output.Color.GREEN == Fore.GREEN
        assert output.Color.MAGENTA == Fore.MAGENTA
        assert output.Color.BLUE == Fore.BLUE
        assert output.Color.YELLOW == Fore.YELLOW
        assert output.Color.BLACK == Fore.BLACK

        assert output.Color.BRIGHT_RED == Style.BRIGHT + Fore.RED
        assert output.Color.BRIGHT_BLUE == Style.BRIGHT + Fore.BLUE
        assert output.Color.BRIGHT_YELLOW == Style.BRIGHT + Fore.YELLOW
        assert output.Color.BRIGHT_GREEN == Style.BRIGHT + Fore.GREEN
        assert output.Color.BRIGHT_CYAN == Style.BRIGHT + Fore.CYAN
        assert output.Color.BRIGHT_WHITE == Style.BRIGHT + Fore.WHITE
        assert output.Color.BRIGHT_MAGENTA == Style.BRIGHT + Fore.MAGENTA

    with monkeypatch.context() as mpc:
        mpc.setenv(const.ENV_PDBSTORE_COLOR_DARK, "1")
        reload(output)
        assert output.Color.RED == Fore.RED
        assert output.Color.WHITE == Fore.BLACK
        assert output.Color.CYAN == Fore.BLUE
        assert output.Color.GREEN == Fore.GREEN
        assert output.Color.MAGENTA == Fore.MAGENTA
        assert output.Color.BLUE == Fore.BLUE
        assert output.Color.YELLOW == Fore.MAGENTA
        assert output.Color.BLACK == Fore.BLACK

        assert output.Color.BRIGHT_RED == Style.BRIGHT + Fore.RED
        assert output.Color.BRIGHT_BLUE == Style.BRIGHT + Fore.BLUE
        assert output.Color.BRIGHT_YELLOW == Fore.MAGENTA
        assert output.Color.BRIGHT_GREEN == Fore.GREEN
        assert output.Color.BRIGHT_CYAN == Fore.BLUE
        assert output.Color.BRIGHT_WHITE == Fore.BLACK
        assert output.Color.BRIGHT_MAGENTA == Style.BRIGHT + Fore.MAGENTA


@mock.patch("pdbstore.io.colors.is_terminal")
def test_construct_color(_is_terminal):
    """test object initialization without colors"""
    _is_terminal.return_value = True
    output.PDBStoreOutput.define_log_level("VV")
    out = output.PDBStoreOutput("my scope")
    assert out.stream == sys.stderr
    assert out.scope == "my scope"
    assert out.output_level() == output.LEVEL_TRACE
    assert _is_terminal.called
    assert out.color is True
    assert out.is_terminal is False
    out.scope = "new scope"
    assert out.scope == "new scope"
    output.PDBStoreOutput.define_log_level("status")


@mock.patch("pdbstore.io.colors.is_terminal")
def test_construct_no_color(_is_terminal):
    """test object initialization without colors"""
    _is_terminal.return_value = False
    out = output.PDBStoreOutput()
    assert out.stream == sys.stderr
    assert out.scope == ""
    assert out.output_level() == output.LEVEL_STATUS
    assert _is_terminal.called
    assert out.color is False
    assert out.is_terminal is False


def test_level_name():
    """test level names mapping"""
    for level in [
        "quiet",
        "error",
        "warning",
        "notice",
        "status",
        None,
        "verbose",
        "debug",
        "V",
        "trace",
        "VV",
    ]:
        output.PDBStoreOutput.define_log_level(level)

    with pytest.raises(exceptions.PDBStoreException):
        output.PDBStoreOutput.define_log_level("unsupported_name")


def test_allowed_level():
    """test if level allowed based on config"""
    output.PDBStoreOutput.define_log_level("error")
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_QUIET) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_ERROR) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_WARNING) is False
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_NOTICE) is False
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_STATUS) is False
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_VERBOSE) is False
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_DEBUG) is False
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_TRACE) is False

    output.PDBStoreOutput.define_log_level("debug")
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_QUIET) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_ERROR) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_WARNING) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_NOTICE) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_STATUS) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_VERBOSE) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_DEBUG) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_TRACE) is False

    output.PDBStoreOutput.define_log_level("status")
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_QUIET) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_ERROR) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_WARNING) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_NOTICE) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_STATUS) is True
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_VERBOSE) is False
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_DEBUG) is False
    assert output.PDBStoreOutput.level_allowed(output.LEVEL_TRACE) is False


@mock.patch("pdbstore.io.colors.is_terminal")
def test_write(_is_terminal, capsys):
    """test write function"""
    _is_terminal.return_value = True
    out = output.PDBStoreOutput()

    output.PDBStoreOutput.define_log_level("error")
    out.write("my message")
    assert capsys.readouterr().err == "" and capsys.readouterr().out == ""

    output.PDBStoreOutput.define_log_level("debug")
    out.write("my message")
    assert capsys.readouterr().err == "my message" and capsys.readouterr().out == ""

    out.write("my message", output.Color.RED)
    assert capsys.readouterr().err == "\x1b[31mmy message\x1b[0m"
    assert capsys.readouterr().out == ""

    out.write("my message", None, output.Color.RED)
    assert capsys.readouterr().err == "\x1b[31mmy message\x1b[0m"
    assert capsys.readouterr().out == ""

    out.write("my message", output.Color.RED, output.Color.RED)
    assert capsys.readouterr().err == "\x1b[31m\x1b[31mmy message\x1b[0m"
    assert capsys.readouterr().out == ""


def test_rewrite_line(capsys):
    """test rewrite function"""
    out = output.PDBStoreOutput()
    out.rewrite_line(
        "Cum deceperit tempore collegam provincia se Retinete quam sociis perfecisse ipsa"
        " sociis etiam ille deceperit se non tegitur lege se de cum modo hostis tempore de"
        " de frui hostis pluris."
    )
    assert (
        capsys.readouterr().err
        == "\rCum deceperit tempore collegam p ... empore de de frui hostis pluris. "
    )
    assert capsys.readouterr().out == ""


@mock.patch("pdbstore.io.colors.is_terminal")
def test_write_message(_is_terminal, capsys):
    """test write_message function"""
    # pylint: disable=protected-access
    _is_terminal.return_value = False
    out = output.PDBStoreOutput("scope")
    out._write_message("my message", output.Color.RED, output.Color.RED)
    assert capsys.readouterr().err == "scope: my message\n"
    assert capsys.readouterr().out == ""

    out._write_message({"key1": "value1", "key2": "value2"}, output.Color.RED, output.Color.RED)
    assert capsys.readouterr().err == "scope: => key1: value1, key2: value2\n"
    assert capsys.readouterr().out == ""

    out = output.PDBStoreOutput()
    out._write_message("my message")
    assert capsys.readouterr().err == "my message\n"
    assert capsys.readouterr().out == ""

    _is_terminal.return_value = True
    out = output.PDBStoreOutput("scope")
    out._write_message("my message", output.Color.RED, output.Color.RED)
    assert (
        capsys.readouterr().err
        == "\x1b[31m\x1b[31mscope:\x1b[0m \x1b[31m\x1b[31mmy message\x1b[0m\n"
    )
    assert capsys.readouterr().out == ""

    out._write_message({"key1": "value1", "key2": "value2"}, output.Color.RED, output.Color.RED)
    assert (
        capsys.readouterr().err
        == "\x1b[31m\x1b[31mscope:\x1b[0m \x1b[31m\x1b[31m=> key1: value1, key2: value2\x1b[0m\n"
    )
    assert capsys.readouterr().out == ""


def _invoke_func(level_name, func_name):
    output.PDBStoreOutput.define_log_level(level_name)
    out = output.PDBStoreOutput()
    func = getattr(out, func_name)
    func("test output message")
    output.PDBStoreOutput.define_log_level("status")
    if func_name == "error":
        return "ERROR: "
    if func_name == "warning":
        return "WARNING: "
    return ""


@pytest.mark.parametrize(
    "params",
    [
        ["trace", "trace", True],
        ["trace", "debug", True],
        ["trace", "verbose", True],
        ["trace", "info", True],
        ["trace", "warning", True],
        ["trace", "error", True],
        ["debug", "trace", False],
        ["debug", "debug", True],
        ["debug", "verbose", True],
        ["debug", "info", True],
        ["debug", "warning", True],
        ["debug", "error", True],
        ["verbose", "trace", False],
        ["verbose", "debug", False],
        ["verbose", "verbose", True],
        ["verbose", "info", True],
        ["verbose", "warning", True],
        ["verbose", "error", True],
        ["info", "trace", False],
        ["info", "debug", False],
        ["info", "verbose", False],
        ["info", "info", True],
        ["info", "highlight", True],
        ["info", "success", True],
        ["info", "warning", True],
        ["info", "error", True],
        ["notice", "trace", False],
        ["notice", "debug", False],
        ["notice", "verbose", False],
        ["notice", "info", False],
        ["notice", "highlight", True],
        ["notice", "success", True],
        ["notice", "warning", True],
        ["notice", "error", True],
        ["warning", "trace", False],
        ["warning", "debug", False],
        ["warning", "verbose", False],
        ["warning", "info", False],
        ["warning", "highlight", False],
        ["warning", "success", False],
        ["warning", "warning", True],
        ["warning", "error", True],
        ["error", "trace", False],
        ["error", "debug", False],
        ["error", "verbose", False],
        ["error", "info", False],
        ["error", "highlight", False],
        ["error", "success", False],
        ["error", "warning", False],
        ["error", "error", True],
        ["quiet", "trace", False],
        ["quiet", "debug", False],
        ["quiet", "verbose", False],
        ["quiet", "info", False],
        ["quiet", "highlight", False],
        ["quiet", "success", False],
        ["quiet", "warning", False],
        ["quiet", "error", False],
    ],
)
@mock.patch("pdbstore.io.colors.is_terminal")
def test_output_per_level(_is_terminal, params, capsys):
    """test trace function"""

    _is_terminal.return_value = False
    prefix = _invoke_func(params[0], params[1])
    out, err = capsys.readouterr()
    assert err == (f"{prefix}test output message\n" if params[2] else "")
    assert out == ""

    _is_terminal.return_value = True
    prefix = _invoke_func(params[0], params[1])
    out, err = capsys.readouterr()
    assert _is_terminal.called
    if params[2]:
        assert f"{prefix}test output message" in err
    else:
        assert err == ""
    assert out == ""


@pytest.mark.parametrize(
    "params",
    [
        ["trace", True],
        ["debug", True],
        ["verbose", True],
        ["info", True],
        ["notice", True],
        ["warning", False],
        ["error", False],
        ["quiet", False],
    ],
)
@mock.patch("pdbstore.io.colors.is_terminal")
def test_title(_is_terminal, params, capsys):
    """test trace function"""
    _is_terminal.return_value = False
    output.PDBStoreOutput.define_log_level(params[0])
    output.PDBStoreOutput().title("TITLE")
    out, err = capsys.readouterr()
    assert err == ("\n======== TITLE ========\n" if params[1] else "")
    assert out == ""

    output.PDBStoreOutput().subtitle("SUBTITLE")
    out, err = capsys.readouterr()
    assert err == ("\n-------- SUBTITLE --------\n" if params[1] else "")
    assert out == ""

    _is_terminal.return_value = True
    output.PDBStoreOutput().title("TITLE")
    out, err = capsys.readouterr()
    assert err == ("\x1b[1m\x1b[35m\n======== TITLE ========\x1b[0m\n" if params[1] else "")
    assert out == ""

    output.PDBStoreOutput().subtitle("SUBTITLE")
    out, err = capsys.readouterr()
    assert err == ("\x1b[1m\x1b[35m\n-------- SUBTITLE --------\x1b[0m\n" if params[1] else "")
    assert out == ""
    output.PDBStoreOutput.define_log_level("status")

    output.PDBStoreOutput().flush()


@mock.patch("pdbstore.io.colors.is_terminal")
def test_cli_out(_is_terminal, capsys):
    """test cli stdout stream"""
    _is_terminal.return_value = False
    output.cli_out_write("my message")
    out, err = capsys.readouterr()
    assert err == ""
    assert out == "my message\n"

    output.cli_out_write("my message", indentation=4)
    out, err = capsys.readouterr()
    assert err == ""
    assert out == "    my message\n"

    _is_terminal.return_value = True
    output.cli_out_write("my message", fore=output.Color.RED)
    out, err = capsys.readouterr()
    assert err == ""
    assert out == "\x1b[31mmy message\x1b[0m\n"

    output.cli_out_write("my message", fore=output.Color.RED, indentation=4)
    out, err = capsys.readouterr()
    assert err == ""
    assert out == "    \x1b[31mmy message\x1b[0m\n"

import sys
from unittest import mock

from pdbstore import const
from pdbstore.io import colors


@mock.patch("colorama.init")
@mock.patch("pdbstore.io.colors.is_terminal")
def test_default_confi_color(_is_terminal, _init):
    """test with default logic"""
    _is_terminal.return_value = True
    colors.init_colorama(sys.stderr)
    assert _init.called
    assert _is_terminal.called


@mock.patch("colorama.init")
@mock.patch("pdbstore.io.colors.is_terminal")
def test_default_confi_no_color(_is_terminal, _init):
    """test with default logic"""
    _is_terminal.return_value = False
    colors.init_colorama(sys.stderr)
    assert _init.called is False
    assert _is_terminal.called


@mock.patch("pdbstore.io.colors.is_terminal")
def test_with_env(_is_terminal, monkeypatch):
    """test using an environment variable"""
    with monkeypatch.context() as mpc:
        mpc.setenv(const.ENV_CLICOLOR_FORCE, "1")
        with mock.patch("colorama.init") as _init:
            colors.init_colorama(sys.stderr)
        assert _init.asset_called_with(False, False, False, True)
        assert _is_terminal.called is False

    with monkeypatch.context() as mpc:
        mpc.setenv(const.ENV_NO_COLOR, "1")
        with mock.patch("colorama.init") as _init:
            colors.init_colorama(sys.stderr)
        assert _init.asset_called_with(False, None, None, True)
        assert _is_terminal.called is False


@mock.patch("colorama.init")
@mock.patch("pdbstore.io.colors.is_terminal")
def test_with_env_no_color(_is_terminal, _init, monkeypatch):
    """test using an environment variable"""
    with monkeypatch.context() as mpc:
        mpc.setenv(const.ENV_NO_COLOR, "1")
        colors.init_colorama(sys.stderr)
        assert _init.called
        assert _is_terminal.called is False

from unittest import mock


@mock.patch("setuptools.setup")
def test_setup(_setup):
    """test and validate setup.py"""
    import setup  # noqa: F401 # pylint: disable=unused-import, import-outside-toplevel

    _setup.assert_called_once_with(
        packages=mock.ANY,
        package_data=mock.ANY,
    )

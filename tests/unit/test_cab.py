import importlib
from unittest import mock

import pytest

import pdbstore.io.cab
from pdbstore import exceptions

# pylint: disable=protected-access


@mock.patch("pdbstore.util.which")
@pytest.mark.parametrize(
    "test_args",
    [
        (
            "linux",
            "/usr/bin/gcab",
            pdbstore.io.cab._compress_gcab,
        ),
        (
            "windows",
            r"C:\Windows\System32\makecab.exe",
            pdbstore.io.cab._compress_makecab,
        ),
    ],
)
def test_compress_supported_per_platform(_which, test_args):
    """test compression is supported"""
    _which.return_value = test_args[1]
    with mock.patch("sys.platform", test_args[0]):
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.cab.compress is not None
        assert pdbstore.io.cab.compress.__name__ == test_args[2].__name__


@mock.patch("pdbstore.util.which")
@pytest.mark.parametrize("platform", ["linux", "windows"])
def test_compress_not_supported_per_platform(_which, platform):
    """test compression is not supported"""
    _which.return_value = None
    with mock.patch("sys.platform", platform):
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.is_compression_supported() is False


@mock.patch("pdbstore.util.which")
def test_compress_linux_invocation_success(_which, fake_process):
    """test linux compression with success"""
    _which.return_value = "/usr/bin/gcab"

    fake_process.register(
        [
            "gcab",
            "-z",
            "-n",
            "-c",
            "/usr/output/file.pd_",
            "/usr/input/file.pdb",
        ],
        stdout=b"compression ok",
        returncode=0,
    )
    with mock.patch("sys.platform", "linux"):
        importlib.reload(pdbstore.io.cab)
        assert (  # pylint: disable=comparison-with-callable
            pdbstore.io.cab.compress == pdbstore.io.cab._compress_gcab
        )
        pdbstore.io.cab.compress("/usr/input/file.pdb", "/usr/output/file.pd_")


@mock.patch("pdbstore.util.which")
def test_compress_linux_invocation_failure(_which):
    """test linux compression with failure"""
    _which.return_value = None

    with mock.patch("sys.platform", "linux"):
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.cab.compress is None
        assert pdbstore.io.is_compression_supported() is False


@mock.patch("pdbstore.util.which")
@pytest.mark.parametrize(
    "test_args",
    [
        (
            "linux",
            "/usr/bin/gcab",
            pdbstore.io.cab._compress_gcab,
            [
                "gcab",
                "-z",
                "-n",
                "-c",
                "/usr/output/file.pd_",
                "/usr/input/file.pdb",
            ],
        ),
        (
            "windows",
            r"C:\Windows\System32\makecab.exe",
            pdbstore.io.cab._compress_makecab,
            [
                "makecab.exe",
                "/D",
                "CompressionType=LZX",
                "/D",
                "CompressionMemory=21",
                "/usr/input/file.pdb",
                "/usr/output/file.pd_",
            ],
        ),
    ],
)
def test_compress_invocation_success(_which, fake_process, test_args):
    """test compression with success"""
    _which.return_value = test_args[1]

    fake_process.register(
        test_args[3],
        stdout=b"compression ok",
        returncode=0,
    )
    with mock.patch("sys.platform", test_args[0]):
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.cab.compress is not None
        assert pdbstore.io.cab.compress.__name__ == test_args[2].__name__
        pdbstore.io.cab.compress("/usr/input/file.pdb", "/usr/output/file.pd_")


@mock.patch("pdbstore.util.which")
@pytest.mark.parametrize(
    "test_args",
    [
        (
            "linux",
            "/usr/bin/gcab",
            pdbstore.io.cab._compress_gcab,
            [
                "gcab",
                "-z",
                "-n",
                "-c",
                "/usr/output/file.pd_",
                "/usr/input/file.pdb",
            ],
        ),
        (
            "windows",
            r"C:\Windows\System32\makecab.exe",
            pdbstore.io.cab._compress_makecab,
            [
                "makecab.exe",
                "/D",
                "CompressionType=LZX",
                "/D",
                "CompressionMemory=21",
                "/usr/input/file.pdb",
                "/usr/output/file.pd_",
            ],
        ),
    ],
)
def test_compress_invocation_failure(_which, fake_process, test_args):
    """test compression with failure"""
    _which.return_value = test_args[1]

    fake_process.register(
        test_args[3],
        stdout="compression error for /usr/input/file.pdb",
        returncode=1,
    )
    with mock.patch("sys.platform", test_args[0]):
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.cab.compress.__name__ == test_args[2].__name__
        with pytest.raises(exceptions.CabCompressionError) as excinfo:
            pdbstore.io.cab.compress("/usr/input/file.pdb", "/usr/output/file.pd_")
        assert str(excinfo.value) == "compression error for /usr/input/file.pdb"


@mock.patch("pdbstore.util.which")
@pytest.mark.parametrize(
    "test_args",
    [
        (
            "linux",
            "/usr/bin/gcab",
            pdbstore.io.cab._decompress_gcab,
        ),
        (
            "windows",
            r"C:\Windows\System32\expand.exe",
            pdbstore.io.cab._decompress_expand,
        ),
    ],
)
def test_decompress_supported_per_platform(_which, test_args):
    """test decompression is supported"""
    _which.return_value = test_args[1]
    with mock.patch("sys.platform", test_args[0]):
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.cab.decompress is not None
        assert pdbstore.io.cab.decompress.__name__ == test_args[2].__name__


@mock.patch("pdbstore.util.which")
@pytest.mark.parametrize("platform", ["linux", "windows"])
def test_decompress_not_supported_per_platform(_which, platform):
    """test compression is not supported"""
    _which.return_value = None
    with mock.patch("sys.platform", platform):
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.is_decompression_supported() is False


@mock.patch("pdbstore.util.which")
@pytest.mark.parametrize(
    "test_args",
    [
        (
            "linux",
            "/usr/bin/gcab",
            pdbstore.io.cab._decompress_gcab,
            [
                "gcab",
                "-x",
                "-C",
                "/usr/output",
                "/usr/input/file.pd_",
            ],
        ),
        (
            "windows",
            r"C:\Windows\System32\expand.exe",
            pdbstore.io.cab._decompress_expand,
            [
                "expand.exe",
                "-R",
                "/usr/input/file.pd_",
                "/usr/output",
            ],
        ),
    ],
)
def test_decompress_invocation_success(_which, fake_process, test_args):
    """test compression with success"""
    _which.return_value = test_args[1]

    fake_process.register(
        test_args[3],
        stdout=b"compression ok",
        returncode=0,
    )
    with mock.patch("sys.platform", test_args[0]):
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.cab.decompress is not None
        assert pdbstore.io.cab.decompress.__name__ == test_args[2].__name__
        pdbstore.io.cab.decompress("/usr/input/file.pd_", "/usr/output")


@mock.patch("pdbstore.util.which")
@pytest.mark.parametrize(
    "test_args",
    [
        (
            "linux",
            "/usr/bin/gcab",
            pdbstore.io.cab._decompress_gcab,
            [
                "gcab",
                "-x",
                "-C",
                "/usr/output",
                "/usr/input/file.pd_",
            ],
        ),
        (
            "windows",
            r"C:\Windows\System32\expand.exe",
            pdbstore.io.cab._decompress_expand,
            [
                "expand.exe",
                "-R",
                "/usr/input/file.pd_",
                "/usr/output",
            ],
        ),
    ],
)
def test_decompress_invocation_failure(_which, fake_process, test_args):
    """test compression with failure"""
    _which.return_value = test_args[1]

    fake_process.register(
        test_args[3],
        stdout="decompression error for /usr/input/file.pd_",
        returncode=1,
    )
    with mock.patch("sys.platform", test_args[0]):
        importlib.reload(pdbstore.io.cab)
        assert pdbstore.io.cab.decompress.__name__ == test_args[2].__name__
        with pytest.raises(exceptions.CabCompressionError) as excinfo:
            pdbstore.io.cab.decompress("/usr/input/file.pd_", "/usr/output")
        assert str(excinfo.value) == "decompression error for /usr/input/file.pd_"

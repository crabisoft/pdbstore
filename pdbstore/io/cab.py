import os
import subprocess
import sys

from pdbstore import exceptions, util
from pdbstore.typing import Callable, PathLike, Union

__all__ = ["compress", "decompress"]

# By default, compression is not supported until we detect the appropriate exectuable
compress: Union[None, Callable[[PathLike, PathLike], None]] = None  # pylint: disable=invalid-name

# By default, decompression is not supported until we detect the appropriate exectuable
decompress: Union[None, Callable[[PathLike, PathLike], None]] = None  # pylint: disable=invalid-name


def _compress_makecab(src_path: PathLike, dest_path: PathLike) -> None:
    """Compress an input file using makecab.exe utility.

    :param src_path: Path to the input file to be compressed
    :param dest_path: Path to the output file
    :raise:
        :CabCompressionError: Failed to execute makecab utility
    """
    args = [
        "makecab.exe",
        "/D",
        "CompressionType=LZX",
        "/D",
        "CompressionMemory=21",
        os.fspath(src_path),
        os.fspath(dest_path),
    ]

    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        out, _ = proc.communicate()

        if proc.returncode != 0:
            raise exceptions.CabCompressionError(f"{out.decode()}")


def _decompress_expand(src_path: PathLike, dest_dir: PathLike) -> None:
    """Decompress an input file using expand.exe utility.

    :param src_path: Path to the input file to be decompressed
    :param dest_dir: Path to the output directory
    :raise:
        :CabCompressionError: Failed to execute makecab utility
    """
    args = [
        "expand.exe",
        "-R",
        os.fspath(src_path),
        os.fspath(dest_dir),
    ]

    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        out, _ = proc.communicate()

        if proc.returncode != 0:
            raise exceptions.CabCompressionError(f"{out.decode()}")


def _compress_gcab(src_path: PathLike, dest_path: PathLike) -> None:
    """
    Compress using GCab

    :param src_path: Path to the input file to be compressed
    :param dest_path: Path to the output file
    :raise:
        :CabCompressionError: Failed to execute makecab utility
    """
    # -z: ZIP compression
    # -n: Store file name only
    # -c: Create cab file
    args = ["gcab", "-z", "-n", "-c", os.fspath(dest_path), os.fspath(src_path)]

    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        out, _ = proc.communicate()

        if proc.returncode != 0:
            raise exceptions.CabCompressionError(f"{out.decode('utf-8')}")


def _decompress_gcab(src_path: PathLike, dest_dir: PathLike) -> None:
    """
    Compress using GCab

    :param src_path: Path to the input file to be compressed
    :param dest_path: Path to the output directory
    :raise:
        :CabCompressionError: Failed to execute makecab utility
    """
    # -x: Extract file
    # -C: Change working directory
    args = ["gcab", "-x", "-C", os.fspath(dest_dir), os.fspath(src_path)]

    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        out, _ = proc.communicate()

        if proc.returncode != 0:
            raise exceptions.CabCompressionError(f"{out.decode('utf-8')}")


if sys.platform == "windows":
    if util.which("makecab") is not None:
        compress = _compress_makecab
    if util.which("expand") is not None:
        decompress = _decompress_expand
else:
    if util.which("gcab") is not None:
        compress = _compress_gcab
        decompress = _decompress_gcab

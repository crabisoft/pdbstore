"""Cab compressor driving the platform utility."""

from pdbstore import exceptions
from pdbstore.adapters.symsrv.compression import Compressor
from pdbstore.io import cab
from pdbstore.io import file as fileinfo
from pdbstore.typing import PathLike

__all__ = ["CabCompressor"]


class CabCompressor(Compressor):
    """Produce and expand cab archives using ``makecab`` or ``gcab``.

    Which utility is available is decided when :mod:`pdbstore.io.cab` is first
    imported, and every call resolves through the module rather than binding at
    import time — so a machine gaining or losing the utility, and a test
    substituting it, are both handled.
    """

    def is_compression_supported(self) -> bool:
        """Determine whether compression is available on this machine.

        :return: True when a file can be compressed, else False.
        """
        return cab.compress is not None

    def is_decompression_supported(self) -> bool:
        """Determine whether decompression is available on this machine.

        :return: True when an archive can be expanded, else False.
        """
        return cab.decompress is not None

    def source_size(self, file_path: PathLike) -> int:
        """Measure a file about to be compressed.

        :param file_path: Path to the file to be measured.
        :return: The size in bytes, or 0 when the file cannot be read.
        """
        return fileinfo.get_file_size(file_path)

    def compress(self, source_path: PathLike, archive_path: PathLike) -> None:
        """Compress a file into a cab archive.

        :param source_path: Path to the file to be compressed.
        :param archive_path: Path of the archive to be produced.
        :raise:
            :CompressionNotSupportedError: No compression utility was found.
            :CabCompressionError: The utility reported a failure.
        """
        if cab.compress is None:  # pragma: no cover
            raise exceptions.CompressionNotSupportedError()
        cab.compress(source_path, archive_path)

    def decompress(self, archive_path: PathLike, dest_dir: PathLike) -> None:
        """Expand a cab archive into a directory.

        :param archive_path: Path to the archive to be expanded.
        :param dest_dir: Path to the destination directory.
        :raise:
            :DecompressionNotSupportedError: No decompression utility was found.
            :CabCompressionError: The utility reported a failure.
        """
        if cab.decompress is None:
            raise exceptions.DecompressionNotSupportedError()
        cab.decompress(archive_path, dest_dir)

"""Compression of the symbols held by a SymSrv store.

SymSrv stores may hold a symbol as a cab archive named ``foo.pd_`` instead of
the plain ``foo.pdb``. Producing one means driving an external utility, so the
gateway states what it needs here and a driver provides it.

Declared next to its consumer rather than in the use case layer: no interactor
ever compresses anything, that is entirely a property of how this particular
store format holds its bytes.
"""

from abc import ABC, abstractmethod

from pdbstore.typing import PathLike

__all__ = ["Compressor"]


class Compressor(ABC):
    """Compress and decompress the files held by a symbol store."""

    @abstractmethod
    def is_compression_supported(self) -> bool:
        """Determine whether compression is available on this machine.

        :return: True when a file can be compressed, else False.
        """

    @abstractmethod
    def is_decompression_supported(self) -> bool:
        """Determine whether decompression is available on this machine.

        :return: True when an archive can be expanded, else False.
        """

    @abstractmethod
    def source_size(self, file_path: PathLike) -> int:
        """Measure a file about to be compressed.

        Needed because cab archives top out at 2GB, past which compression has
        to be turned off rather than attempted and failed.

        :param file_path: Path to the file to be measured.
        :return: The size in bytes, or 0 when the file cannot be read.
        """

    @abstractmethod
    def compress(self, source_path: PathLike, archive_path: PathLike) -> None:
        """Compress a file into an archive.

        :param source_path: Path to the file to be compressed.
        :param archive_path: Path of the archive to be produced.
        :raise:
            :CompressionNotSupportedError: Compression is unavailable.
            :CabCompressionError: The utility reported a failure.
        """

    @abstractmethod
    def decompress(self, archive_path: PathLike, dest_dir: PathLike) -> None:
        """Expand an archive into a directory.

        :param archive_path: Path to the archive to be expanded.
        :param dest_dir: Path to the destination directory.
        :raise:
            :DecompressionNotSupportedError: Decompression is unavailable.
            :CabCompressionError: The utility reported a failure.
        """

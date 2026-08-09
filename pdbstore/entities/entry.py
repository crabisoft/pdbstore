"""A single file referenced by a transaction."""

import os
from pathlib import Path

from pdbstore import util
from pdbstore.entities import symsrv_layout
from pdbstore.typing import Optional, PathLike

__all__ = ["TransactionEntry"]


class TransactionEntry:
    """A file referenced by a transaction of a symbol store.

    The entry knows *where* it belongs inside the store, expressed as a key,
    but never reads or writes anything. Storing and extracting the bytes is
    the responsibility of a
    :class:`SymbolStoreGateway <pdbstore.usecases.gateways.symbol_store.SymbolStoreGateway>`.
    """

    MAX_COMPRESSED_FILE_SIZE: int = 2147482624
    """Largest file size that may be compressed.

    Cab archives are limited to 2GB as per Microsoft documentation, so beyond
    that size compression has to be turned off.
    """

    def __init__(
        self,
        file_name: str,
        file_hash: str,
        source_file: PathLike,
        compressed: bool = False,
    ):
        # The associated file name
        self.file_name: str = file_name
        # The associated file hash
        self.file_hash: str = file_hash
        # Full path name to the input source file to be stored
        self.source_file: Path = util.str_to_path(source_file)
        # Flag indicating if the stored file is compressed or not
        self.compressed: bool = compressed

    @property
    def file_path(self) -> Path:
        """Retrieve the original file path.

        :return: The original file path
        """
        return self.source_file

    @property
    def dir_key(self) -> str:
        """Retrieve the store key of the directory holding this entry.

        :return: The store key of the entry directory
        """
        return symsrv_layout.entry_dir_key(self.file_name, self.file_hash)

    @property
    def stored_key(self) -> str:
        """Retrieve the store key under which this entry is stored.

        :return: The store key of the entry
        """
        return symsrv_layout.entry_key(self.file_name, self.file_hash, self.compressed)

    @property
    def stored_name(self) -> str:
        """Retrieve the file name this entry takes inside the store.

        :return: The stored file name, compressed or not
        """
        return symsrv_layout.entry_file_name(self.file_name, self.compressed)

    @property
    def rel_path(self) -> Path:
        """Retrieve the store-relative path to the stored file.

        :return: Relative path name to the stored file
        """
        return Path(*symsrv_layout.split_key(self.stored_key))

    def is_compressed(self) -> bool:
        """Determine if compression activated or not

        :return: True if compression is enabled, else False
        """
        return self.compressed

    def exceeds_compression_limit(self, file_size: int) -> bool:
        """Determine whether a file is too large to be compressed.

        :param file_size: The size of the file to be stored, in bytes.
        :return: True when compression must be disabled, else False
        """
        return self.MAX_COMPRESSED_FILE_SIZE < file_size

    def clone(
        self,
        promoted: Optional[bool] = False,
        source_file: Optional[PathLike] = None,
    ) -> "TransactionEntry":
        """Clone the transaction entry.

        :param promoted: True when the clone is fed by an already stored file,
            in which case the clone is held uncompressed by the target store.
        :param source_file: Origin recorded for the clone. A promotion passes
            the location the content was taken from, since the original input
            file is long gone by then.
        :return: The cloned :class:`TransactionEntry` object
        """
        return TransactionEntry(
            self.file_name,
            self.file_hash,
            self.source_file if source_file is None else source_file,
            False if promoted else self.compressed,
        )

    def __str__(self) -> str:
        """Get text representation

        :return: String representing this object
        """
        return f'"{self.file_name}\\{self.file_hash}","{self.source_file.absolute()}"'

    def __repr__(self) -> str:
        """Get text representation from a TransactionEntry object."""
        return str(self)

    @staticmethod
    def parse_line(line: str) -> Optional["TransactionEntry"]:
        """Build a transaction entry from one line of a transaction file.

        :param line: The line to be parsed.
        :return: The :class:`TransactionEntry` object if successful, else None
        """
        fields = [field.strip('"') for field in line.strip().split(",")]
        if not fields or not fields[0]:
            return None
        file_name, file_hash = fields[0].split("\\")
        source_file = fields[1] if len(fields) > 1 else ""
        return TransactionEntry(file_name, file_hash, source_file)

    @staticmethod
    def file_name_of(file_path: PathLike) -> str:
        """Extract the entry file name out of an input file path.

        :param file_path: Path to the input file.
        :return: The base name of ``file_path``
        """
        return os.path.basename(os.fspath(file_path))

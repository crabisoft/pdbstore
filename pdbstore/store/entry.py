"""Store-bound transaction entry.

.. deprecated::
    The entry itself now lives in :mod:`pdbstore.entities.entry` and performs
    no input/output. This subclass keeps the historical API — an entry that
    knows its store and can read and write itself — by delegating to the
    gateway of the store it belongs to.

    ``stored_path`` only means something for a store held on a local
    filesystem. Code meant to work against any backend should use
    ``stored_key`` and go through the gateway.
"""

from pathlib import Path

from pdbstore.entities.entry import TransactionEntry as _TransactionEntry
from pdbstore.typing import Optional, PathLike, TYPE_CHECKING
from pdbstore.usecases import lookup

if TYPE_CHECKING:  # pragma: no cover
    from pdbstore.store.store import Store


__all__ = ["TransactionEntry"]


class TransactionEntry(_TransactionEntry):
    """A transaction entry bound to the store holding it."""

    def __init__(
        self,
        store: "Store",
        file_name: str,
        file_hash: str,
        source_file: PathLike,
        compressed: bool = False,
    ):
        super().__init__(file_name, file_hash, source_file, compressed)
        # The associated symbol store object
        self.store: "Store" = store

    @classmethod
    def of(
        cls,
        store: "Store",
        entry: _TransactionEntry,
    ) -> "TransactionEntry":
        """Bind a plain entry to a store.

        :param store: The store holding ``entry``.
        :param entry: The entry to be bound.
        :return: The store-bound :class:`TransactionEntry` object.
        """
        return cls(store, entry.file_name, entry.file_hash, entry.source_file, entry.compressed)

    @property
    def stored_path(self) -> Path:
        """Retrieve the full path to the stored file.

        :return: Full path name to the stored file
        """
        return self.store.path_of(self.stored_key)

    def is_committed(self) -> bool:
        """Determine if this entry has been commit on the disk or not

        :return: True if this entry is valid/published, else False
        """
        return self.store.gateway.entry_exists(self)

    def commit(
        self,
        force: Optional[bool] = False,
        store: Optional["Store"] = None,
        skip_if_exists: Optional[bool] = False,
    ) -> bool:
        """Store the file referenced by this entry into the symbol store.

        :param force: `True` to overwrite any existing file from the store.
        :param store: Optional source :class:`Store <pdbstore.store.store.Store>`
            to promote the file from.
        :param skip_if_exists: `True` to skip an already stored file.
        :return: `True` if the file is stored successfully, else `False`.
        :raise:
            :CabCompressionError: The entry cannot be compressed.
            :CopyFileError: The entry content cannot be stored.
        """
        return self.store.gateway.store_entry(
            self,
            force,
            store.gateway if store is not None else None,
            skip_if_exists,
        )

    def extract(self, dest_dir: PathLike) -> Optional[PathLike]:
        """Extract file from store to specific directory.

        :param dest_dir: Path to output directory
        :return: Path to the output file if successful, else None
        :raise:
            :DecompressionNotSupportedError: Decompression is not supported
            :CabCompressionError: The entry cannot be decompressed.
            :CopyFileError: The entry cannot be copied out.
        """
        return self.store.gateway.extract_entry(self, dest_dir)

    def get_disk_usage(self) -> int:
        """Compute the disk space usage related to this transaction entry

        :return: The disk space usage in bytes.
        """
        stat = self.store.gateway.entry_stat(self)
        return stat.size if stat else 0

    def clone(  # type: ignore[override] # pylint: disable=arguments-renamed
        self,
        store: Optional["Store"] = None,
        promoted: Optional[bool] = False,
    ) -> "TransactionEntry":
        """Clone the transaction entry.

        :param store: Optional :class:`Store <pdbstore.store.store.Store>` object to be
                      associated to the cloned entry
        :param promoted: True when the clone is fed by an already stored file.
        :return: The cloned :class:`TransactionEntry` object
        """
        return TransactionEntry(
            store or self.store,
            self.file_name,
            self.file_hash,
            self.stored_path if promoted else self.source_file,
            False if promoted else self.compressed,
        )

    @staticmethod
    def load(
        store: "Store",
        file_name: str,
        file_hash: str,
        source_file: PathLike,
    ) -> "TransactionEntry":
        """Load transaction entry from the store.

        :param store: The associated Store object
        :param file_name: The file name for the transaction entry
        :param file_hash: The file hash
        :param source_file: Full path to the input source file
        :return: The new :class:`TransactionEntry` object
        """
        return TransactionEntry(
            store,
            file_name,
            file_hash,
            source_file,
            store.gateway.is_entry_compressed(file_name, file_hash),
        )

    @staticmethod
    def create(store: "Store", file_path: PathLike) -> Optional["TransactionEntry"]:
        """Create a new transaction entry given store and file path.

        :param store: The associated Store object
        :param file_path: The file name for the transaction entry
        :return: :class:`TransactionEntry` object if successful, else None
        :raise:
            :FileNotExistsError: The specified file doesn't exists
        """
        entry = lookup.build_entry(store.gateway, store.state.reader, file_path)
        if entry is None:
            return None
        return TransactionEntry.of(store, entry)

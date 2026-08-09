"""Gateway giving access to a symbol store.

This is the only gateway the business interactors depend on. It speaks in
transactions and entries, never in paths or keys, so that swapping the
underlying storage leaves every use case untouched.

The contract is deliberately made of persistence primitives: allocating an
identifier, loading and appending transactions, storing and extracting an
entry. Orchestration — deciding which transactions to delete, how a promotion
composes, when a commit is complete — belongs to the interactors and is
therefore written once for every backend.
"""

from abc import ABC, abstractmethod

from pdbstore.entities.entry import TransactionEntry
from pdbstore.entities.transaction import Transaction, TransactionBinding
from pdbstore.typing import BinaryIO, Dict, List, Optional, PathLike, Sequence
from pdbstore.usecases.gateways.blob_store import BlobStat

__all__ = ["SymbolStoreGateway"]


class SymbolStoreGateway(TransactionBinding, ABC):
    """Persist and retrieve the transactions of a symbol store.

    Implementations also act as the
    :class:`TransactionBinding <pdbstore.entities.transaction.TransactionBinding>`
    of the transactions they hand out, which is what lets a transaction resolve
    its own entries lazily without knowing where they live.
    """

    @property
    @abstractmethod
    def location(self) -> str:
        """Describe where this store keeps its data.

        :return: A human readable location, such as a directory or a URI.
        """

    @abstractmethod
    def display_path(self, key: str) -> str:
        """Render a store key the way an end user expects to see it.

        Reporting only: a local store names a path, a remote one names a URI.
        Never parse the result — it is not a key.

        :param key: The key to be rendered.
        :return: A human readable location for ``key``.
        """

    @abstractmethod
    def open_entry(self, stored_key: str) -> BinaryIO:
        """Open the content of a stored entry for streamed reading.

        This is what lets a transaction be carried over to another store
        without either side assuming the bytes ever touch a local disk.

        :param stored_key: The key of the stored entry.
        :return: A binary stream over the stored content.
        :raise:
            :ReadFileError: The entry cannot be read.
        """

    @abstractmethod
    def prepare(self) -> None:
        """Create whatever structure the store needs before being written to.

        :raise:
            :UnexpectedError: The store structure cannot be created.
        """

    @property
    @abstractmethod
    def next_transaction_id(self) -> str:
        """Peek at the identifier the next transaction will receive.

        Calling this repeatedly yields the same value until a transaction is
        actually committed through :meth:`commit_transaction_id`.

        :return: The next transaction id, formatted over 10 digits.
        :raise:
            :ReadFileError: The last identifier cannot be read.
            :UnexpectedError: The last identifier is not a number.
        """

    @abstractmethod
    def commit_transaction_id(self, transaction_id: str) -> None:
        """Record an identifier as the last one allocated.

        :param transaction_id: The transaction id that was just used.
        :raise:
            :WriteFileError: The store bookkeeping cannot be updated.
            :UnexpectedError: The identifier is empty.
        """

    @abstractmethod
    def load_transactions(self) -> Dict[str, Transaction]:
        """Load every active transaction, indexed by identifier.

        :return: The transactions listed by the store, in file order.
        :raise:
            :ReadFileError: The transaction listing cannot be read.
        """

    @abstractmethod
    def load_history(self) -> List[Transaction]:
        """Load the full history, including delete operations.

        :return: The transactions in chronological order.
        :raise:
            :ReadFileError: The history cannot be read.
        """

    @abstractmethod
    def append_transaction(self, transaction: Transaction) -> None:
        """Add a transaction to the active listing.

        :param transaction: The transaction to be listed.
        :raise:
            :WriteFileError: The listing cannot be updated.
        """

    @abstractmethod
    def rewrite_transactions(self, transactions: Sequence[Transaction]) -> None:
        """Replace the active listing with the given transactions.

        :param transactions: The transactions that remain active.
        :raise:
            :WriteFileError: The listing cannot be rewritten.
        """

    @abstractmethod
    def append_history(self, line: str) -> None:
        """Add one raw line to the history.

        :param line: The line to be recorded.
        :raise:
            :WriteFileError: The history cannot be updated.
        """

    @abstractmethod
    def write_entries(self, transaction: Transaction) -> None:
        """Record the entries referenced by a committed transaction.

        :param transaction: The transaction whose entries must be recorded.
        :raise:
            :WriteFileError: The entries cannot be recorded.
        """

    @abstractmethod
    def load_entries(self, transaction: Transaction) -> List[TransactionEntry]:
        """Load the entries referenced by a transaction.

        :param transaction: The transaction to be resolved.
        :return: The referenced entries, empty when the transaction is not
            committed or holds none.
        :raise:
            :ReadFileError: The entries cannot be read.
        """

    @abstractmethod
    def is_deleted(self, transaction: Transaction) -> bool:
        """Determine whether a transaction has been marked as deleted.

        :param transaction: The transaction to be inspected.
        :return: True when the transaction is deleted, else False.
        """

    @abstractmethod
    def is_promoted(self, transaction: Transaction) -> bool:
        """Determine whether a transaction has been marked as promoted.

        :param transaction: The transaction to be inspected.
        :return: True when the transaction is promoted, else False.
        """

    @abstractmethod
    def mark_deleted(self, transaction: Transaction) -> None:
        """Mark a transaction as deleted.

        :param transaction: The transaction to be marked.
        :raise:
            :RenameFileError: The transaction cannot be marked.
        """

    @abstractmethod
    def mark_promoted(self, transaction: Transaction) -> None:
        """Mark a transaction as promoted.

        :param transaction: The transaction to be marked.
        :raise:
            :RenameFileError: The transaction cannot be marked.
        """

    @abstractmethod
    def entry_exists(self, entry: TransactionEntry) -> bool:
        """Determine whether an entry is already stored.

        :param entry: The entry to be checked.
        :return: True when the entry content is present, else False.
        """

    @abstractmethod
    def is_entry_compressed(self, file_name: str, file_hash: str) -> bool:
        """Determine whether a symbol is held compressed in this store.

        Answered by the store rather than carried by the entry, because
        whether a given symbol was compressed is a property of how it was
        stored, not of the file being looked up.

        :param file_name: The original file name.
        :param file_hash: The file signature.
        :return: True when the symbol is stored as a cab archive, else False.
        """

    @abstractmethod
    def entry_stat(self, entry: TransactionEntry) -> Optional[BlobStat]:
        """Retrieve the metadata of a stored entry.

        :param entry: The entry to be inspected.
        :return: The metadata if the entry is stored, else None.
        """

    @abstractmethod
    def store_entry(
        self,
        entry: TransactionEntry,
        force: Optional[bool] = False,
        source: Optional["SymbolStoreGateway"] = None,
        skip_if_exists: Optional[bool] = False,
    ) -> bool:
        """Store the content of an entry.

        When ``source`` is given the content is taken from that store rather
        than from the local source file, which is how a promotion carries an
        already stored file over to another store.

        :param entry: The entry to be stored.
        :param force: True to overwrite an already stored file, else False.
        :param source: Optional store to take the content from.
        :param skip_if_exists: True to report an already stored entry as
            skipped instead of successful.
        :return: True when the entry counts as stored, else False.
        :raise:
            :CabCompressionError: The entry cannot be compressed.
            :CopyFileError: The entry content cannot be stored.
        """

    @abstractmethod
    def extract_entry(self, entry: TransactionEntry, dest_dir: PathLike) -> Optional[PathLike]:
        """Extract a stored entry into a local directory.

        :param entry: The entry to be extracted.
        :param dest_dir: Path to the destination directory.
        :return: Path to the extracted file if successful, else None.
        :raise:
            :DecompressionNotSupportedError: Decompression is unavailable.
            :CabCompressionError: The entry cannot be decompressed.
            :CopyFileError: The entry cannot be copied out.
        """

    @abstractmethod
    def has_entry_content(self, entry_dir_key: str) -> bool:
        """Determine whether anything is stored for one entry.

        :param entry_dir_key: The key of the entry directory, as computed by
            :func:`pdbstore.entities.symsrv_layout.entry_dir_key`.
        :return: True when content is stored under that key, else False.
        """

    @abstractmethod
    def delete_entry_content(self, entry_dir_key: str) -> bool:
        """Remove the stored content of one entry.

        :param entry_dir_key: The key of the entry directory, as computed by
            :func:`pdbstore.entities.symsrv_layout.entry_dir_key`.
        :return: True when something was removed, else False.
        """

    @abstractmethod
    def reset(self) -> None:
        """Drop everything cached in memory, forcing a reload on next access."""

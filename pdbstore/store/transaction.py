"""Store-bound transaction.

.. deprecated::
    The transaction itself now lives in :mod:`pdbstore.entities.transaction`
    and performs no input/output. This subclass keeps the historical API — a
    transaction that knows its store and can commit itself — by delegating to
    the gateway of the store it belongs to.
"""

from datetime import datetime

from pdbstore import io
from pdbstore.entities.summary import Summary
from pdbstore.entities.transaction import Transaction as _Transaction
from pdbstore.entities.transaction import TransactionRegEx
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.store.entry import TransactionEntry
from pdbstore.typing import cast, List, Optional, PathLike, TYPE_CHECKING, Union
from pdbstore.usecases.commit import CommitTransactionInteractor

if TYPE_CHECKING:  # pragma: no cover
    from pdbstore.store.store import Store


__all__ = ["Transaction", "TransactionRegEx"]


class Transaction(_Transaction):
    """A transaction bound to the store holding it."""

    def __init__(
        self,
        store: "Store",
        transaction_id: Union[str, None] = None,
        transaction_type: TransactionType = TransactionType.ADD,
        ref: str = "file",
        timestamp: Union[datetime, None] = None,
        product: Union[str, None] = None,
        version: Union[str, None] = None,
        comment: Union[str, None] = None,
        deleted_id: Union[str, None] = None,
    ):
        super().__init__(
            transaction_id,
            transaction_type,
            ref,
            timestamp,
            product,
            version,
            comment,
            deleted_id,
            binding=store.gateway if store is not None else None,
        )
        self.store: "Store" = store

    @classmethod
    def of(
        cls,
        store: "Store",
        transaction: _Transaction,
    ) -> "Transaction":
        """Bind a plain transaction to a store.

        :param store: The store holding ``transaction``.
        :param transaction: The transaction to be bound.
        :return: The store-bound :class:`Transaction` object.
        """
        if isinstance(transaction, cls):
            return transaction
        bound = cls(
            store,
            transaction.transaction_id,
            transaction.transaction_type,
            transaction.ref,
            transaction.timestamp,
            transaction.product,
            transaction.version,
            transaction.comment,
            transaction.deleted_id,
        )
        bound.transactions_entries = [
            TransactionEntry.of(store, entry) for entry in transaction.transactions_entries
        ]
        return bound

    @property
    def entries(self) -> List[TransactionEntry]:  # type: ignore[override]
        """Retrieve the list of associated entries

        :return: List of associated
            :class:`TransactionEntry <pdbstore.store.entry.TransactionEntry>` objects
        """
        if not self.transactions_entries and self.binding is not None and not self.is_deleted():
            self.transactions_entries = [
                TransactionEntry.of(self.store, entry) for entry in self.binding.load_entries(self)
            ]
        return cast(List[TransactionEntry], self.transactions_entries)

    def register_entry(self, pathname: PathLike, compress: bool = False) -> bool:
        """Register a new transaction entry

        :param pathname: Path to the file
        :param compress: True to compress it, else False
        :return: True if successful, else False
        :raise:
            :FileNotExistsError: The specified file doesn't exists
        """
        hash_value = io.file.compute_hash_key(pathname)
        if not hash_value:
            return False

        self.add_entry(
            TransactionEntry(
                self.store,
                TransactionEntry.file_name_of(pathname),
                hash_value,
                pathname,
                compress,
            )
        )
        return True

    def commit(
        self,
        transaction_id: str,
        timestamp: datetime,
        force: Optional[bool] = False,
        store: Optional["Store"] = None,
    ) -> Summary:
        """Save the transaction into the store.

        :param transaction_id: The transaction ID
        :param timestamp: The transaction date/time
        :param force: True to overwrite files already present in the store.
        :param store: Optional source :class:`Store <pdbstore.store.store.Store>`
            to promote the files from.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object
        :raise:
            :WriteFileError: Failed to update the store bookkeeping
        """
        # pylint: disable=protected-access
        return CommitTransactionInteractor(self.store.state)._store_entries(
            self,
            transaction_id,
            timestamp,
            force,
            store.gateway if store is not None else None,
        )

    def mark_deleted(self) -> None:
        """Tag this transaction as deleted.

        :raise:
            :RenameFileError: Failed to rename the transaction file
        """
        self.store.gateway.mark_deleted(self)

    def mark_promoted(self) -> None:
        """Tag this transaction as promoted.

        :raise:
            :RenameFileError: Failed to rename the transaction file
        """
        self.store.gateway.mark_promoted(self)

    def compute_disk_usage(self) -> int:
        """Compute the disk space usage related to all files associated to
        this transaction

        :return: The disk space usage in bytes.
        """
        return sum(entry.get_disk_usage() for entry in self.entries)

    @staticmethod
    def parse_line(  # type: ignore[override] # pylint: disable=arguments-renamed
        store: "Store", line: str
    ) -> Union["Transaction", None]:
        """Parse a transaction entry from the store listing.

        :param store: The associated :class:`Store <pdbstore.store.store.Store>` object
        :param line: the line to be parsed
        :return: The corresponding Transaction object if successful, else None
        """
        parsed = _Transaction.parse_line(line)
        if parsed is None:
            return None
        return Transaction.of(store, parsed)

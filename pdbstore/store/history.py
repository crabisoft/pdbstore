"""Store-bound history.

.. deprecated::
    The history is now read and written through the symbol store gateway. This
    class keeps the historical API by delegating to it.
"""

from pdbstore.entities import symsrv_layout
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.store.transaction import Transaction
from pdbstore.typing import Any, cast, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from pdbstore.store.store import Store


__all__ = ["History"]


class History:
    """The full operation history of a symbol store."""

    def __init__(self, store: "Store"):
        self.store: "Store" = store

    def file_exists(self) -> bool:
        """Determine whether the history file exists or not

        :return: True if the file exists, else False
        """
        return self.store.gateway.blob.is_blob(symsrv_layout.history_key())

    @property
    def transactions(self) -> List[Transaction]:
        """Get the transactions list."""
        return cast(List[Transaction], self.store.state.history)

    @property
    def transactions_list(self) -> List[Transaction]:
        """Get the transactions list.

        .. deprecated:: Use :attr:`transactions` instead.
        """
        return self.transactions

    def __len__(self) -> int:
        """Retrieve the total number of transactions."""
        return len(self.transactions)

    def __getitem__(self, item: int) -> Transaction:
        """Retrieve a transaction given its zero-based index."""
        return self.transactions[item]

    def add(self, transaction: Any) -> None:
        """Register a new 'add' operation

        :param transaction: The transaction to be added.
        :raise:
            :WriteFileError: Failed to update history file
        """
        self.store.gateway.append_history(f"{transaction}")
        if isinstance(transaction, Transaction):
            self.store.state.remember_history(transaction)

    def delete(self, transaction: Transaction, delete_id: str) -> None:
        """Register a new 'del' operation

        :param transaction: The deleted transaction.
        :param delete_id: The transaction id associated to new history entry.
        :raise:
            :WriteFileError: Failed to update history file.
        """
        self.store.gateway.append_history(f"{delete_id},del,{transaction.id}")
        self.store.state.remember_history(
            Transaction(
                self.store,
                delete_id,
                TransactionType.DEL,
                deleted_id=transaction.id,
            )
        )

    def reset(self) -> None:
        """Reset to the transactions list to `None`."""
        self.store.state.reset()

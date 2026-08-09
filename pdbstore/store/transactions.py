"""Store-bound collection of transactions.

.. deprecated::
    The queries themselves now live in :mod:`pdbstore.usecases.lookup` and the
    deletion logic in :mod:`pdbstore.usecases.delete`. This class keeps the
    historical API by delegating to them.
"""

from pdbstore.entities.summary import Summary
from pdbstore.store.transaction import Transaction
from pdbstore.typing import Dict, ItemsView, List, Optional, TYPE_CHECKING
from pdbstore.usecases import lookup
from pdbstore.usecases.delete import DeleteTransactionInteractor
from pdbstore.usecases.lookup import FilesUsage

if TYPE_CHECKING:  # pragma: no cover
    from pdbstore.store.store import Store


__all__ = ["FilesUsage", "Transactions"]


class Transactions:
    """The active transactions of a symbol store."""

    def __init__(self, store: "Store"):
        self.store: "Store" = store

    @property
    def count(self) -> int:
        """Retrieve the total number of transactions

        :return: The total number of registered transactions
        """
        return len(self.transactions)

    @property
    def transactions(self) -> Dict[str, Transaction]:
        """Get the Transaction dictionary given by their ID.

        The store listing is loaded and parsed on first access.

        :return: Dictonary containing the
            :class:`Transaction <pdbstore.store.transaction.Transaction>` object for
            a given transaction id.
        """
        return self.store.state.bound_transactions

    def find(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction given by its ID

        :param transaction_id: The transaction ID to be found
        :return: The :class:`Transaction <pdbstore.store.transaction.Transaction>`
          object found if successful, else None
        """
        return self.transactions.get(transaction_id)

    def get_files_usage(self) -> FilesUsage:
        """Build the dictionary of file usage from all registered transactions

        :return: A :class:`FilesUsage` object containing all required information
        """
        return lookup.files_usage(self.transactions)

    def items(self) -> ItemsView[str, Transaction]:
        """Iterate over registered transactions given their ID

        :return: Iterator for iterating over all registered transactions."""
        return self.transactions.items()

    def add(self, transaction: Transaction) -> None:
        """Add new transaction into the store listing

        :param transaction: The transaction object to be added
        :raise:
            :WriteFileError: Failed to update the listing
        """
        self.store.gateway.append_transaction(transaction)
        self.store.state.register(transaction)

    def delete(self, transaction: Transaction, dry_run: bool = False) -> Summary:
        """Delete a transaction.

        :param transaction: The transaction to be deleted
        :param dry_run: True to just print the list of files to be deleted,
                        else False to delete the requested transaction.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object
        :raise:
            :WriteFileError: Failed to update the listing
        """
        # pylint: disable=protected-access
        interactor = DeleteTransactionInteractor(self.store.state)
        summary = interactor._release_files(transaction, dry_run)
        if dry_run:
            return summary

        remaining: List[Transaction] = [
            item for item in self.transactions.values() if item.id != transaction.id
        ]
        self.store.gateway.rewrite_transactions(remaining)
        self.store.state.forget(transaction)
        return summary

    def reset(self) -> None:
        """Reset transactions to an empty dictionary."""
        self.store.state.reset()

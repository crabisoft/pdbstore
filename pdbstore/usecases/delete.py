"""Delete transactions from a symbol store."""

from pdbstore.entities import symsrv_layout
from pdbstore.entities.summary import OpStatus, Summary
from pdbstore.entities.transaction import Transaction
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.exceptions import TransactionNotFoundError
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import List, Optional, Union
from pdbstore.usecases import lookup
from pdbstore.usecases.store_state import StoreState

__all__ = ["CleanOldVersionsInteractor", "DeleteTransactionInteractor"]


class DeleteTransactionInteractor:
    """Remove one transaction and the files it alone keeps alive."""

    def __init__(self, state: StoreState):
        self.state = state

    def execute(self, transaction_id: Union[str, int], dry_run: bool = False) -> Summary:
        """Delete a transaction given by its identifier.

        Deleting a transaction never removes a file another transaction still
        references, so only the files it alone keeps alive are released.

        :param transaction_id: The transaction id to be deleted.
        :param dry_run: True to only report what would be removed.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object.
        :raise:
            :TransactionNotFoundError: The specified transaction cannot be found.
            :ImproperTransactionTypeError: The transaction exists with another type.
            :WriteFileError: The store bookkeeping cannot be updated.
        """
        gateway = self.state.gateway
        transaction = lookup.find_transaction(
            self.state.transactions, transaction_id, TransactionType.ADD
        )

        summary = self._release_files(transaction, dry_run)
        if dry_run:
            return summary

        # Drop the transaction from the active listing.
        remaining = [item for item in self.state.transactions.values() if item.id != transaction.id]
        gateway.rewrite_transactions(remaining)
        self.state.forget(transaction)

        # Tag the transaction as deleted in the store itself.
        gateway.mark_deleted(transaction)

        # Record the deletion as a new history operation.
        next_transaction_id = gateway.next_transaction_id
        gateway.append_history(f"{next_transaction_id},del,{transaction.id}")
        self.state.remember_history(
            Transaction(
                next_transaction_id,
                TransactionType.DEL,
                deleted_id=transaction.id,
                binding=gateway,
            )
        )
        gateway.commit_transaction_id(next_transaction_id)
        return summary

    def _release_files(self, transaction: Transaction, dry_run: bool) -> Summary:
        """Remove the stored files that only ``transaction`` references."""
        gateway = self.state.gateway
        unused_list = lookup.files_usage(self.state.transactions).find_unused_entries(transaction)

        summary = Summary(
            transaction.transaction_id,
            OpStatus.SUCCESS,
            TransactionType.DEL,
            references=transaction.count,
        )

        for file_name, file_hash in unused_list:
            dir_key = symsrv_layout.entry_dir_key(file_name, file_hash)
            display = gateway.display_path(dir_key)
            if dry_run:
                status = (
                    OpStatus.SUCCESS if gateway.has_entry_content(dir_key) else OpStatus.SKIPPED
                )
                summary.add_file(display, status)
                continue
            if gateway.delete_entry_content(dir_key):
                summary.add_file(display, OpStatus.SUCCESS)
            else:
                summary.add_file(display, OpStatus.SKIPPED)

        return summary


class CleanOldVersionsInteractor:
    """Keep only the most recent transactions of a product version."""

    def __init__(self, state: StoreState):
        self.state = state

    def execute(
        self,
        product: str,
        version: str,
        keep: int,
        comment: Optional[str] = None,
        dry_run: bool = False,
    ) -> Summary:
        """Remove the transactions exceeding a retention count.

        :param product: The product name.
        :param version: The product version.
        :param keep: How many transactions to preserve for that version.
        :param comment: Optional comment the transactions must carry to be
            eligible. Ignored when None.
        :param dry_run: True to only report what would be removed.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object.
        """
        transactions = [
            item
            for item in self.state.transactions.values()
            if item.product == product
            and item.version == version
            and not item.is_deleted()
            and (not comment or item.comment == comment)
        ]
        if not transactions or len(transactions) < keep:
            return Summary(None, OpStatus.SKIPPED, TransactionType.DEL)

        # Allocate the identifier once so every deletion shares the same run.
        self.state.gateway.next_transaction_id  # pylint: disable=pointless-statement

        deleter = DeleteTransactionInteractor(self.state)
        summaries: List[Summary] = []
        for transaction in transactions[:-keep]:
            try:
                summaries.append(deleter.execute(int(transaction.id), dry_run))
            except TransactionNotFoundError:
                PDBStoreOutput().warning(f"no transaction with id '{transaction.id}' found")
                summaries.append(
                    Summary(
                        transaction.id,
                        OpStatus.FAILED,
                        TransactionType.DEL,
                        f"no transaction with id '{transaction.id}' found",
                    )
                )

        return chain_summaries(summaries)


def chain_summaries(summaries: List[Summary]) -> Summary:
    """Link a list of summaries together and return the first one.

    :param summaries: The summaries to be linked, in order.
    :return: The head of the chain, or an empty summary when there is none.
    """
    for previous, current in zip(summaries, summaries[1:]):
        previous.linked = current
    return summaries[0] if summaries else Summary()

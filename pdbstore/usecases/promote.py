"""Promote a transaction from one symbol store to another."""

from pdbstore.entities.summary import OpStatus, Summary
from pdbstore.entities.transaction import Transaction
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import Optional
from pdbstore.usecases.commit import CommitTransactionInteractor
from pdbstore.usecases.gateways.symbol_store import SymbolStoreGateway
from pdbstore.usecases.store_state import StoreState

__all__ = ["PromoteTransactionInteractor"]


class PromoteTransactionInteractor:
    """Copy a transaction of a snapshot store into a release store.

    The files are taken from the source store rather than from the original
    input files, which are long gone by then. Because both stores are reached
    through the same gateway, a promotion works between any two backends.
    """

    def __init__(self, state: StoreState):
        self.state = state

    def execute(
        self,
        transaction: Optional[Transaction],
        source: SymbolStoreGateway,
        comment: Optional[str] = None,
    ) -> Summary:
        """Promote a transaction into the target store.

        :param transaction: The transaction to be promoted.
        :param source: The store currently holding ``transaction``.
        :param comment: Optional comment for the newly created transaction.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object.
        """
        if not transaction:
            return Summary(None, OpStatus.FAILED, None, "Invalid transaction object")
        if transaction.transaction_type != TransactionType.ADD:
            return Summary(None, OpStatus.FAILED, None, "Invalid transaction type")

        if not comment:
            comment = f"{transaction.comment} : " if transaction.comment else ""
            comment += f"Promote {transaction.transaction_id} from {source.location}"

        PDBStoreOutput().info(f"Promoting {transaction.transaction_id} from {source.location} ...")

        new_transaction = Transaction(
            transaction_type=TransactionType.ADD,
            product=transaction.product or "",
            version=transaction.version or "",
            comment=comment,
            binding=self.state.gateway,
        )

        for entry in transaction.entries:
            new_transaction.add_entry(entry.clone(True, source.display_path(entry.stored_key)))

        summary = CommitTransactionInteractor(self.state).execute(new_transaction, True, source)
        if summary.status == OpStatus.SUCCESS:
            source.mark_promoted(transaction)
        return summary

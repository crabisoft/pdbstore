"""Commit a transaction into a symbol store."""

import concurrent.futures as cf
import time
from datetime import datetime

from pdbstore import util
from pdbstore.entities.entry import TransactionEntry
from pdbstore.entities.summary import OpStatus, Summary
from pdbstore.entities.transaction import Transaction
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.exceptions import PDBStoreException
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import Any, Optional, Tuple, Union
from pdbstore.usecases.gateways.symbol_store import SymbolStoreGateway
from pdbstore.usecases.store_state import StoreState

__all__ = ["CommitTransactionInteractor"]


class CommitTransactionInteractor:
    """Publish a transaction and the files it references into a store."""

    def __init__(self, state: StoreState):
        self.state = state
        self.gateway = state.gateway

    def execute(
        self,
        transaction: Transaction,
        force: Optional[bool] = False,
        source: Optional[SymbolStoreGateway] = None,
    ) -> Summary:
        """Commit a transaction.

        When ``source`` is given, the referenced files are taken from that
        store instead of from local input files, which is how a promotion
        carries a transaction over.

        :param transaction: The transaction to be committed.
        :param force: True to overwrite files already present in the store.
        :param source: Optional store holding the files to be carried over.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object.
        :raise:
            :UnexpectedError: The store structure cannot be created.
            :WriteFileError: The store bookkeeping cannot be updated.
            :ReadFileError: The last transaction identifier cannot be read.
        """
        self.gateway.prepare()

        now = round(time.time())
        summary = self._store_entries(
            transaction,
            self.gateway.next_transaction_id,
            datetime.fromtimestamp(now),
            force,
            source,
        )
        if summary.status == OpStatus.SUCCESS:
            # Publish the transaction, then stamp the store as modified.
            self.gateway.append_transaction(transaction)
            self.gateway.append_history(f"{transaction}")
            self.gateway.commit_transaction_id(transaction.id)
            self.state.register(transaction)

        return summary

    def _store_entries(
        self,
        transaction: Transaction,
        transaction_id: str,
        timestamp: datetime,
        force: Optional[bool] = False,
        source: Optional[SymbolStoreGateway] = None,
    ) -> Summary:
        """Store every file referenced by a transaction."""
        summary = Summary(transaction_id, OpStatus.SKIPPED, TransactionType.ADD)

        if transaction.is_committed():
            PDBStoreOutput().warning(
                f"Transction ID {transaction.transaction_id} is already committed, so ignore it",
            )
            summary.status = OpStatus.SKIPPED
            return summary
        if not transaction.transactions_entries:
            PDBStoreOutput().warning("no entry defined, so not possible to commit on the disk")
            summary.status = OpStatus.SKIPPED
            return summary

        self.gateway.prepare()
        transaction.mark_committed(transaction_id, timestamp)

        # Symbol files are large and independent from each other, so storing
        # them concurrently is where nearly all the wall clock time is won.
        with cf.ThreadPoolExecutor() as executor:
            for entry, result in executor.map(
                lambda item: self._store_entry(item, force, source),
                transaction.entries,
            ):
                if isinstance(result, OpStatus):
                    summary.add_entry(
                        entry,
                        result,
                        TransactionType.ADD,
                        source_stat=self._source_stat(entry, result),
                    )
                    if result == OpStatus.SUCCESS:
                        summary.status = OpStatus.SUCCESS
                else:
                    summary.status = OpStatus.FAILED
                    summary.add_entry(entry, OpStatus.FAILED, TransactionType.ADD)
                    PDBStoreOutput().error(result)

        if summary.success(True) > 0:
            self.gateway.write_entries(transaction)
        return summary

    def _store_entry(
        self,
        entry: TransactionEntry,
        force: Optional[bool] = False,
        source: Optional[SymbolStoreGateway] = None,
    ) -> Tuple[TransactionEntry, Union[OpStatus, PDBStoreException]]:
        """Store one entry, reporting the failure rather than raising it."""
        try:
            return (
                entry,
                (
                    OpStatus.SUCCESS
                    if self.gateway.store_entry(entry, force, source)
                    else OpStatus.SKIPPED
                ),
            )
        except PDBStoreException as exc:  # pragma: no cover
            return (entry, exc)

    @staticmethod
    def _source_stat(entry: TransactionEntry, status: OpStatus) -> Optional[Any]:
        """Read the metadata of the input file, when there is one to read."""
        if status != OpStatus.SUCCESS:
            return None
        source = util.str_to_path(entry.file_path)
        if source is None:
            return None
        try:
            return source.stat()
        except OSError:
            return None

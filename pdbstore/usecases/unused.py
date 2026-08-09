"""Find the stored files that have not been used for a while."""

import time

from pdbstore import util
from pdbstore.entities.summary import OpStatus, Summary
from pdbstore.entities.transaction import Transaction
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.exceptions import PDBStoreException
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import Dict, List
from pdbstore.usecases import lookup
from pdbstore.usecases.delete import DeleteTransactionInteractor
from pdbstore.usecases.store_state import StoreState

__all__ = ["FindUnusedFilesInteractor"]


class FindUnusedFilesInteractor:
    """Report, and optionally release, the files nobody has read recently.

    Symbol stores accumulate: a build from two years ago still occupies space
    even though no debugger has asked for it since. The access time of the
    stored file is what tells them apart.
    """

    def __init__(self, state: StoreState):
        self.state = state

    def execute(self, unused_since: float, delete: bool = False) -> Summary:
        """Find the files not accessed since a given date.

        :param unused_since: The cut-off date, as a POSIX timestamp. Files last
            accessed before it are reported.
        :param delete: True to also remove the reported files, and the
            transactions left without any file.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object.
        """
        output = PDBStoreOutput()
        gateway = self.state.gateway
        summary = Summary(None, OpStatus.SUCCESS, TransactionType.UNUSED)

        obsolete_transactions: List[Transaction] = []
        deletion_dict: Dict[str, int] = {}

        for transaction, entry in lookup.iterate(
            self.state.transactions, lambda item: not item.is_deleted()
        ):
            try:
                output.verbose(f"checking {entry.rel_path} ...")
                stat = gateway.entry_stat(entry)
                if stat is None or stat.atime >= unused_since:
                    continue

                dct = summary.add_file(entry.rel_path, OpStatus.SUCCESS)
                dct["date"] = time.strftime("%Y-%m-%d", time.localtime(stat.atime))
                dct["transaction_id"] = transaction.id
                if not delete:
                    dct["file_size"] = stat.size
                    continue

                # The content itself is released by deleting the transaction
                # below, which is the only step that knows whether another
                # transaction still references the file.
                count = deletion_dict.get(transaction.id, 0) + 1
                deletion_dict[transaction.id] = count
                if count == transaction.count:
                    # Every file of the transaction is gone, so is the transaction.
                    obsolete_transactions.append(transaction)
                dct["del_size"] = stat.size
            except PDBStoreException as exp:  # pragma: no cover
                summary.add_file(
                    util.path_to_str(entry.rel_path), OpStatus.FAILED, "ex:" + str(exp)
                )
            except Exception as exc:  # pylint: disable=broad-except # pragma: no cover
                summary.add_file(util.path_to_str(entry.rel_path), OpStatus.FAILED, str(exc))
                output.error(exc)
                output.error(f"unexpected error when checking {entry.rel_path} file usage")

        deleter = DeleteTransactionInteractor(self.state)
        for transaction in obsolete_transactions:
            deleter.execute(transaction.id)
        return summary

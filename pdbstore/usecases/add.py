"""Add symbol files to a symbol store."""

from pdbstore.entities.entry import TransactionEntry
from pdbstore.entities.summary import OpStatus, Summary
from pdbstore.entities.transaction import Transaction
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.exceptions import PDBStoreException, UnknowFileTypeError
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import List, Optional, PathLike, Tuple
from pdbstore.usecases.commit import CommitTransactionInteractor
from pdbstore.usecases.delete import CleanOldVersionsInteractor
from pdbstore.usecases.store_state import StoreState

__all__ = ["AddSymbolsInteractor"]


class AddSymbolsInteractor:
    """Register input files as a new transaction and publish it."""

    def __init__(self, state: StoreState):
        self.state = state

    def execute(
        self,
        files: List[PathLike],
        product: str,
        version: str,
        comment: Optional[str] = None,
        compress: bool = False,
        force: bool = False,
        keep_count: int = 0,
    ) -> Summary:
        """Add files to the store as a single transaction.

        A file that cannot be identified is reported and skipped rather than
        aborting the whole transaction, so one bad input does not cost a build
        its symbols.

        :param files: The input files to be stored.
        :param product: The product name.
        :param version: The product version.
        :param comment: Optional comment for the transaction.
        :param compress: True to store the files as cab archives.
        :param force: True to overwrite files already present in the store.
        :param keep_count: When positive, how many transactions of that product
            version to preserve once this one is published.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object.
        """
        output = PDBStoreOutput()
        gateway = self.state.gateway

        # Allocate the identifier up front so it is reported even when nothing
        # ends up being stored.
        gateway.next_transaction_id  # pylint: disable=pointless-statement

        transaction = Transaction(
            transaction_type=TransactionType.ADD,
            product=product,
            version=version,
            comment=comment or "",
            binding=gateway,
        )

        success = 0
        errors_list: List[Tuple[PathLike, str]] = []
        for file_path in files:
            try:
                if self._register(transaction, file_path, compress):
                    success += 1
            except UnknowFileTypeError as exu:
                output.warning(f"{file_path}: not a known file type")
                errors_list.append((file_path, str(exu)))
            except PDBStoreException as exp:
                output.error(str(exp))
                errors_list.append((file_path, str(exp)))
            except Exception as exg:  # pylint: disable=broad-except # pragma: no cover
                errors_list.append((file_path, str(exg)))
                output.error(f"unexpected error when adding {file_path} with the following error:")
                output.error(exg)

        if success > 0:
            try:
                summary = CommitTransactionInteractor(self.state).execute(transaction, force)
            except PDBStoreException as exc:
                output.error(exc)
                return Summary(transaction.id, OpStatus.FAILED, TransactionType.ADD)
            except Exception as exc:  # pylint: disable=broad-except
                output.error(exc)
                output.error("unexpected error when filling Transaction object")
                return Summary(transaction.id, OpStatus.FAILED, TransactionType.ADD)
        else:
            summary = Summary(None, OpStatus.SKIPPED, TransactionType.ADD)

        for failed_path, message in errors_list:
            summary.add_file(failed_path, OpStatus.FAILED, message)

        if keep_count > 0:
            summary.linked = CleanOldVersionsInteractor(self.state).execute(
                product, version, keep_count
            )

        return summary

    def _register(
        self, transaction: Transaction, file_path: PathLike, compress: bool = False
    ) -> bool:
        """Add one input file to a transaction.

        :param transaction: The transaction being built.
        :param file_path: Path to the input file.
        :param compress: True to store the file as a cab archive.
        :return: True when the file was registered, else False.
        :raise:
            :FileNotExistsError: The specified file doesn't exist.
            :UnknowFileTypeError: Unsupported file type.
        """
        file_hash = self.state.reader.signature_of(file_path)
        if not file_hash:
            return False

        transaction.add_entry(
            TransactionEntry(
                TransactionEntry.file_name_of(file_path),
                file_hash,
                file_path,
                compress,
            )
        )
        return True

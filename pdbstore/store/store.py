import time
from datetime import datetime
from pathlib import Path

from pdbstore import const, exceptions, util
from pdbstore.io import file
from pdbstore.io.output import PDBStoreOutput
from pdbstore.store.entry import TransactionEntry
from pdbstore.store.history import History
from pdbstore.store.summary import OpStatus, Summary
from pdbstore.store.transaction import Transaction
from pdbstore.store.transaction_type import TransactionType
from pdbstore.store.transactions import Transactions
from pdbstore.typing import Callable, Generator, List, Optional, PathLike, Tuple

__all__ = ["Store"]


class Store:
    """Manage symbol store."""

    def __init__(self, store_path: PathLike):
        self.rootdir: Path = util.str_to_path(store_path)
        self.transactions: Transactions = Transactions(self)
        self.history = History(self)
        self._next_transaction_id: Optional[str] = None

    @property
    def admin_dir(self) -> Path:
        """Retrieve the full path name of 000Admin directory"""
        admin_dir_path = self.rootdir / const.ADMIN_DIRNAME
        return admin_dir_path

    @property
    def last_id_file_path(self) -> Path:
        """Retrieve the full path name of lastid.txt"""
        return self.admin_dir / const.LASTID_FILENAME

    @property
    def history_file_path(self) -> Path:
        """Retrieve the full path name of history.txt"""
        return self.admin_dir / const.HISTORY_FILENAME

    @property
    def server_file_path(self) -> Path:
        """Retrieve the full path name of server.txt"""
        return self.admin_dir / const.SERVER_FILENAME

    @property
    def pingme_file_path(self) -> Path:
        """Retrieve the full path name of pingme.txt"""
        return self.rootdir / const.PINGME_FILENAME

    @property
    def next_transaction_id(self) -> str:
        """Generate next valid transaction id

        :return: The next transaction id
        :raise:
            :ReadFileError: Failed to read lastid file
            :UnexpectedError: Failed to convert read string into an integer
        """
        if self._next_transaction_id is None:
            last_id = 0
            if self.last_id_file_path.exists():
                try:
                    content = file.read_text_file(self.last_id_file_path)
                    last_id = int(content)
                except exceptions.ReadFileError:
                    raise
                except Exception as exc:  # pragma: no cover
                    raise exceptions.UnexpectedError(
                        "Failed to extract last id from lastid file"
                    ) from exc

            next_id = last_id + 1
            self._next_transaction_id = f"{next_id:010}"

            PDBStoreOutput().debug(f"{const.LASTID_FILENAME} reported id {next_id}")
            PDBStoreOutput().debug(f"Final id is {self._next_transaction_id}")

        return self._next_transaction_id

    def new_transaction(
        self,
        product: str,
        version: str,
        comment: Optional[str] = None,
        transaction_type: TransactionType = TransactionType.ADD,
    ) -> Transaction:
        """Create a new transaction.

        :param product: The product name
        :param version: The product version
        :param product: The product name
        :param comment: Optional transaction comment
        :param transaction_type: The transaction type. It can be ``add`` or ``del``
        :return: The new :class:`Transaction <pdbstore.store.transaction.Transaction>` object
        """
        return Transaction(
            self,
            transaction_type=transaction_type,
            product=product,
            version=version,
            comment=comment,
        )

    def find_transaction(
        self, transaction_id: int, transaction_type: Optional[TransactionType] = None
    ) -> Transaction:
        """Find an existing transaction given by its id

        :param transaction_id: The transaction id.
        :param transaction_type: Optional transaction type. It can be ``add``,  ``del`` or ``None``.
        :return: A :class:`Transaction <pdbstore.store.transaction.Transaction>` object
                          if `transaction_id` exists, else None
        :raise:
            :TransactionNotFoundError: The specified transition cannot be found.
            :ImproperTransactionTypeError: The specified transition exists but with
                                           a different transaction type.
            :WriteFileError: An error occurs when updating global file.
        """
        trans_id = f"{transaction_id:010d}"
        PDBStoreOutput().debug("Finding ID ... {trans_id}")
        transaction = self.transactions.find(trans_id)
        if not transaction:
            raise exceptions.TransactionNotFoundError(transaction_id)
        if transaction_type and transaction_type.value != transaction.transaction_type.value:
            raise exceptions.ImproperTransactionTypeError(
                transaction_id,
                transaction.transaction_type.value,
                transaction_type.value,
            )
        return transaction

    def delete_transaction(self, transaction_id: int, dry_run: bool = False) -> Summary:
        """Delete an existing transaction given by its id

        :param transaction_id: The transaction id to be deleted.
        :param dry_run: True to just print the list of files to be deleted,
                        else False to delete the requested transaction.
        :return: A :class:`Summary <pdbstore.store.summary.Summary>` object
        :raise:
            :TransactionNotFoundError: The specified transition cannot be found.
            :ImproperTransactionTypeError: The specified transition exists but with
                a different transaction type.
            :WriteFileError: An error occurs when updating global file.
        """
        # Retrieve the Transition object assocaited the specified id
        transaction: Transaction = self.find_transaction(transaction_id, TransactionType.ADD)

        # Remove the transition from the history file
        summary = self.transactions.delete(transaction, dry_run)
        if not dry_run:
            # Tag the transition as deleted on the disk
            transaction.mark_deleted()

            # Add new del entry in the history file
            next_transaction_id = self.next_transaction_id
            self.history.delete(transaction, next_transaction_id)

            self._update_global(next_transaction_id)
        return summary

    def commit(
        self,
        transaction: Transaction,
        force: Optional[bool] = False,
        store: Optional["Store"] = None,
    ) -> Summary:
        """Commit a transaction on the disk.

        If ``store`` is `None`, this function will consider as a standard transaction,
        else this function will promote the files referenced by ``transaction``
        :class:`Transaction <pdbstore.store.transaction.Transaction>` object and stored
        in ``store`` as a new transaction from this
        :class:`Store <pdbstore.store.store.Store>` object.

        :param transaction: The transaction to be committed.
        :param force: True to overwrite any existing file from the store, else False.
        :param store: Optional :class:`Store <pdbstore.store.store.Store>` object
        :return: A :class:`Summary <pdbstore.store.summary.Summary>` object
        :raise:
            :UnexpectedError: Failed to create missing directories or update
                              global files
            :WriteFileError: An error occurs when updating a file
            :ReadFileError: Failed to read lastid file
        """
        # Ensure that directories exists
        try:
            if not self.rootdir.is_dir():
                self.rootdir.mkdir(parents=True)
            if not self.admin_dir.is_dir():
                self.admin_dir.mkdir(parents=True)
        except Exception as exc:
            raise exceptions.UnexpectedError("failed to create symbol store directories") from exc

        # Commit the transaction on the disk
        now = round(time.time())
        summary = transaction.commit(
            self.next_transaction_id, datetime.fromtimestamp(now), force, store
        )
        if summary.status == OpStatus.SUCCESS:
            # Add the transaction into the server file
            self.transactions.add(transaction)
            # Add the transaction into the history file
            self.history.add(transaction)
            # Update the last id and pingme files
            self._update_global(transaction.id)

        return summary

    def fetch_symbol(self, file_path: PathLike) -> Optional[Tuple[Transaction, TransactionEntry]]:
        """Fetch pdb file given an executable file.

        This function will first try to fetch debugging information from `file_path`
        pe file. If exists, the function will search for the required pdb file
        from the store based on extracted information.

        :param file_path: Path to the pe file

        :return: A tuple containing the first transaction if successful, else None.
            The returned tuple is composed by:
            * item[0]: The associated
            :class:`Transaction <pdbstore.store.transaction.Transaction>` object
            * item[1]: The associated
            :class:`TransactionEntry <pdbstore.store.entry.TransactionEntry>` object
        """
        dbg_info = file.extract_dbg_info(file_path)
        if not dbg_info:
            return None

        # Search the first transaction where the file is referenced
        for transaction in self.transactions.transactions.values():
            for entry in transaction.entries:
                if (entry.file_name, entry.file_hash) == dbg_info:
                    return (transaction, entry)

        # Not found
        return None

    def find_entries(
        self, file_path: PathLike, full: Optional[bool] = False
    ) -> List[Tuple[Transaction, TransactionEntry]]:
        """Find a transaction entry given by a file path

        Call this function to retrieve the first or all transaction
        entries associated to `file_path`

        :param file_path: Path to the request file
        :param full: True to retrieve all transaction entries associated
                     to `file_path`, else False to retrieve only the
                     first transaction entry.

        :return: A list of associated transaction entries where for each item:

        * item[0]: The associated
          :class:`Transaction <pdbstore.store.transaction.Transaction>` object
        * item[1]: The associated
          :class:`TransactionEntry <pdbstore.store.entry.TransactionEntry>` object
        """
        entries_list: List[Tuple[Transaction, TransactionEntry]] = []

        # Create transaction entry object for the specified file
        file_entry = TransactionEntry.create(self, file_path)
        if not file_entry:
            PDBStoreOutput().debug(f"failed to create transaction entry from {file_path} file")
            return entries_list

        # Build the list of associated TransactionEntry object associated to
        # the specifie file path
        for transaction in self.transactions.transactions.values():
            for entry in transaction.entries:
                if (entry.file_name, entry.file_hash) == (
                    file_entry.file_name,
                    file_entry.file_hash,
                ):
                    entries_list.append((transaction, entry))
                    if not full:
                        break

        return entries_list

    def _update_global(self, transaction_id: str) -> None:
        """Update lastid and pingme files

        :param transaction_id: The latest transaction id used
        :raise:
            :WriteFileError: An error occurs when updating a file
            :UnexpectedError: Invalid transaction ID
        """
        if not transaction_id:
            raise exceptions.UnexpectedError("Invalid transaction ID")

        try:
            with self.last_id_file_path.open("wt") as fpl:
                fpl.write(transaction_id)
            # Reset last id
            self._next_transaction_id = None
        except Exception as exc:
            PDBStoreOutput().error("failed to update lastid file")
            PDBStoreOutput().debug(f"with the following error: {str(exc)}")
            raise exceptions.WriteFileError(self.last_id_file_path) from exc
        try:
            self.pingme_file_path.touch()
        except Exception as exc:
            PDBStoreOutput().error("failed to touch pingme file")
            raise exceptions.WriteFileError(self.pingme_file_path) from exc

    def remove_old_versions(
        self,
        product: str,
        version: str,
        keep: int,
        comment: Optional[str] = None,
        dry_run: bool = False,
    ) -> Summary:
        """Remove previous transactions associated to a product name and version

        :param product: The product name.
        :param version: The product version.
        :param keep: The maximum number of transactions to keep for the same product
                     name and version.
        :param comment: Optional to filter the transactions to be deleted. Ignored if
                        None.
        :param dry_run: True to just print the list of transactions id to be deleted,
                        else False to delete the requested transactions.
        :return: A :class:`Summary <pdbstore.store.summary.Summary>` object
        """
        # Determine the list of available transactions
        transactions = list(
            filter(
                lambda t: t.product == product
                and t.version == version
                and not t.is_deleted()
                and (not comment or t.comment == comment),
                self.transactions.transactions.values(),
            )
        )
        if not transactions or len(transactions) < keep:
            return Summary(None, OpStatus.SKIPPED, TransactionType.DEL)

        # Generate next transaction id
        self.next_transaction_id  # pylint: disable=pointless-statement

        # Need to delete some transactions
        summary: Optional[Summary] = None
        next_summary: Optional[Summary] = None
        transactions = transactions[:-keep]
        for transaction in transactions:
            try:
                trans_summary = self.delete_transaction(int(transaction.id), dry_run)
            except exceptions.TransactionNotFoundError:
                PDBStoreOutput().warning(f"no transaction with id '{transaction.id}' found")
                trans_summary = Summary(
                    transaction.id,
                    OpStatus.FAILED,
                    TransactionType.DEL,
                    f"no transaction with id '{transaction.id}' found",
                )

            if next_summary:
                next_summary.linked = trans_summary
                next_summary = trans_summary
            else:
                summary = trans_summary
            next_summary = trans_summary

        return summary or Summary()

    def iterator(
        self, filter_cb: Optional[Callable[[Transaction], bool]] = None
    ) -> Generator[Tuple[Transaction, TransactionEntry], None, None]:
        """Iterate over all transactions and file entries.

        :param product: Optional callback function to filter transactions.
        """
        for transaction in self.transactions.transactions.values():
            if not filter_cb or filter_cb(transaction):
                for entry in transaction.entries:
                    yield (transaction, entry)

    def promote_transaction(
        self, transaction: Transaction, comment: Optional[str] = None
    ) -> Summary:
        """Copy an existing transaction from another store.

        This function will clone the ``transaction`` object,
        :param transaction: The :class:`Transaction <pdbstore.store.transaction.Transaction>`
        object to be copied.
        :return: The new :class:`Transaction <pdbstore.store.transaction.Transaction>` object
        from the store
        """

        if not transaction:
            return Summary(None, OpStatus.FAILED, None, "Invalid transaction object")
        if transaction.transaction_type != TransactionType.ADD:
            return Summary(None, OpStatus.FAILED, None, "Invalid transaction type")

        if not comment:
            comment = f"{transaction.comment} : " if transaction.comment else ""
            comment += f"Promote {transaction.transaction_id} from {transaction.store.rootdir}"

        PDBStoreOutput().info(
            f"Promoting {transaction.transaction_id} from {transaction.store.rootdir} ..."
        )

        new_transaction = self.new_transaction(
            transaction.product or "", transaction.version or "", comment
        )

        for entry in transaction.entries:
            new_transaction.add_entry(entry.clone(self, True))

        summary = self.commit(new_transaction, True, transaction.store)
        if summary.status == OpStatus.SUCCESS:
            transaction.mark_promoted()
        return summary

    def check_admin_dir(self) -> None:
        """Check that all required directories exists"""
        if not self.admin_dir.is_dir():
            self.admin_dir.mkdir(parents=True)

    def reset(self) -> None:
        """Reset to an empty store from memory only."""
        self.transactions.reset()
        self.history.reset()
        self._next_transaction_id = None

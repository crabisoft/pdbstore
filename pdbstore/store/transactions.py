""" Manage a set of transactions.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, ItemsView, List, Optional, Tuple

from pdbstore.exceptions import WriteFileError
from pdbstore.io import file
from pdbstore.io.output import PDBStoreOutput
from pdbstore.store.entry import TransactionEntry
from pdbstore.store.summary import OpStatus, Summary
from pdbstore.store.transaction import Transaction
from pdbstore.store.transaction_type import TransactionType

__all__ = ["FilesUsage", "Transactions"]


class FilesUsage:
    """Manage dictionary with all transactions for each file"""

    def __init__(self) -> None:
        self.entries: Dict[Tuple[str, str], List[str]] = {}

    def add_entry(self, entry: TransactionEntry, transaction: Transaction) -> None:
        """Add a new transaction entry given its associated transaction object

        :param entry: The transaction entry object to add
        :param transaction: The transaction object associated to ``entry``
        """
        key = (entry.file_name, entry.file_hash)
        if key not in self.entries:
            self.entries[key] = []

        if transaction.id:
            self.entries[key].append(transaction.id)

    def find_unused_entries(self, transaction: Transaction) -> List[Tuple[str, str]]:
        """Determine the list of entries that are not used anymore from a transaction

        This function will loop over all registered entries and check
        how many transactions are associated to each file. When an entry
        is referenced only once, this function will consider it as unused.

        :param transaction: A :class:`Transaction <pdbstore.store.transaction.Transaction>` object
        :return: List of tuple pairs
        """
        deleted_entries = []

        for entry, ids in self.entries.items():
            if transaction.id in ids:
                if len(ids) == 1:
                    # The entry is used only by the input transaction
                    deleted_entries.append(entry)

        return deleted_entries


class Transactions:
    """A SymbolStore transactions representation"""

    def __init__(self, store: "Store"):  # type: ignore[name-defined]  # noqa: F821
        self.store: "Store" = store  # type: ignore[name-defined] # noqa: F821
        self._transactions: Dict[str, Transaction] = {}

    def _server_file_exists(self) -> bool:
        """Determine whether the server file exists or not

        :return: True if the file exists, else False
        """
        exists: bool = self.store.server_file_path.is_file()
        return exists

    def _parse(self) -> Dict[str, Transaction]:
        """Parser the server file.

        :raise:
            ReadFileError: Failed to read server file
        """
        if not self._server_file_exists():
            PDBStoreOutput().verbose(f"{str(self.store.server_file_path)} not found")
            return {}

        transactions = {}

        for line in file.read_text_file(self.store.server_file_path, True):
            transaction = Transaction.parse_line(self.store, line)
            if transaction and transaction.id:
                transactions[transaction.id] = transaction
        return transactions

    @property
    def transactions(self) -> Dict[str, Transaction]:
        """Get the Transaction dictionary given by their ID.

        If the the server text file will be automatically loaded and parser
        if not done yet

        :return: Dictonary containing the
            :class:`Transaction <pdbstore.store.transaction.Transaction>` object for
            a given transaction id.
        """
        if not self._transactions:
            self._transactions = self._parse()
        return self._transactions

    def find(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction given by its ID

        :param transaction_id: The transaction ID to be found
        :return: The :class:`Transaction <pdbstore.store.transaction.Transaction>`
          object found if successful, else None
        """
        ret = self.transactions.get(transaction_id)
        return ret

    def get_files_usage(self) -> FilesUsage:
        """Build the dictionary of file usage from all registered transactions

        :return: A :class:`FilesUsage` object containing all required information
        """
        fmap = FilesUsage()

        for transaction in self.transactions.values():
            for entry in transaction.entries:
                fmap.add_entry(entry, transaction)

        return fmap

    def items(self) -> ItemsView[str, Transaction]:
        """Iterate over registered transactions given their ID

        :return: Iterator for iterating over all registered transactions."""
        return self.transactions.items()

    def add(self, transaction: Transaction) -> None:
        """Add new transaction into the server file

        :param transaction: The transaction object to be added into server file
        :raise:
            :WriteFileError: Failed to update history file
        """
        try:
            with open(self.store.server_file_path, "ab") as fps:
                fps.write(f"{transaction}{os.linesep}".encode("utf-8"))
            self.transactions[transaction.transaction_id] = transaction
        except Exception as exc:
            raise WriteFileError(None, f"failed to append '{transaction}' in server file") from exc

    def delete(self, transaction: Transaction, dry_run: bool = False) -> Summary:
        """Delete a transaction.

        :param transaction: The transaction to be deleted
        :param dry_run: True to just print the list of files to be deleted,
                        else False to delete the requested transaction.
        :return: A :class:`Summary <pdbstore.store.summary.Summary>` object
        :raise:
            :WriteFileError: Failed to update history file
        """
        # Build the list of unused entries
        unused_list = self.get_files_usage().find_unused_entries(transaction)

        summary = Summary(
            transaction.transaction_id,
            OpStatus.SUCCESS,
            TransactionType.DEL,
            references=transaction.count,
        )

        # delete any unused files
        for fname, fhash in unused_list:
            # Remove the associated directory on the disk
            dir_path: Path = self.store.rootdir / fname / fhash
            if dir_path.is_dir():
                summary.add_file(dir_path, OpStatus.SUCCESS)
                if not dry_run:
                    shutil.rmtree(os.fspath(dir_path))

                    try:
                        parent_dir = os.fspath(dir_path.parent)
                        if len(os.listdir(parent_dir)) == 0:
                            # Remove empty directory
                            shutil.rmtree(parent_dir)
                    except Exception as exc:  # pylint: disable=broad-except
                        PDBStoreOutput().error(exc)
            else:
                summary.add_file(dir_path, OpStatus.SKIPPED)
        if dry_run:
            return summary

        # create a list of transaction without the deleted transaction
        new_transactions = [v for v in self._transactions.values() if v.id != transaction.id]

        # 'delete' transaction listing from server file
        self._rewrite_server_file(new_transactions)

        # Unregister the deleted transaction
        del self._transactions[transaction.id]

        return summary

    def _rewrite_server_file(self, transactions: List[Transaction]) -> None:
        """Overwrite server file given a list of transactions

        :param transactions: List of
        :class:`Transaction <pdbstore.store.transaction.Transaction>` object
        :raise:
            :WriteFileError: Failed to update history file
        """
        try:
            if not self.store.admin_dir.is_dir():
                self.store.admin_dir.mkdir(parents=True)
            with self.store.server_file_path.open("wb") as fpt:
                for transaction in sorted(transactions, key=lambda t: t.id):
                    fpt.write(f"{transaction}{os.linesep}".encode("utf-8"))
        except Exception as exc:
            raise WriteFileError(None, "failed to rewrite the server file") from exc

    def reset(self) -> None:
        """Reset transactions to an empty dictionary."""
        self._transactions = {}

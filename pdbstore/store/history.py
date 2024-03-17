import os
from typing import List, Optional

from pdbstore.exceptions import WriteFileError
from pdbstore.io import file
from pdbstore.io.output import PDBStoreOutput
from pdbstore.store.transaction import Transaction
from pdbstore.store.transaction_type import TransactionType


class History:
    """Manage history.txt content"""

    def __init__(self, store: "Store"):  # type: ignore[name-defined] # noqa: F821
        self.store: "Store" = store  # type: ignore[name-defined] # noqa: F821
        self.transactions_list: Optional[List[Transaction]] = None

    def file_exists(self) -> bool:
        """Determine whether the history file exists or not

        :return: True if the file exists, else False
        """
        exists: bool = self.store.history_file_path.is_file()
        return exists

    @property
    def transactions(self) -> List[Transaction]:
        """Get the transactions list."""
        if self.transactions_list is None:
            self.transactions_list = self._parse()
        return self.transactions_list

    def __len__(self) -> int:
        """Retrieve the total number of transactions."""
        return len(self.transactions)

    def __getitem__(self, item: int) -> Transaction:
        """Retrieve a transaction given its zero-based index."""
        return self.transactions[item]

    def add(self, transaction: Transaction) -> None:
        """Register a new 'add' operation

        :param transaction: The transaction to be added.
        :raise:
            :WriteFileError: Failed to update history file
        """
        self._write_line(f"{transaction}")
        if self.transactions_list is not None:
            self.transactions.append(transaction)

    def delete(self, transaction: Transaction, delete_id: str) -> None:
        """Register a new 'del' operation

        :param transaction: The deleted transaction.
        :param delete_id: The transaction id associated to new history entry.
        :raise:
            :WriteFileError: Failed to update history file.
        """
        self._write_line(f"{delete_id},del,{transaction.id}")
        if self.transactions_list is not None:
            self.transactions.append(
                Transaction(
                    self.store,
                    delete_id,
                    TransactionType.DEL,
                    deleted_id=transaction.id,
                )
            )

    def _parse(self) -> List[Transaction]:
        """Parse history file.
        :return List of loaded :class:`Transaction` objects
        :raise:
            :ReadFileError: Failed to read history file
        """
        if not self.file_exists():
            PDBStoreOutput().debug(f"{self.store.history_file_path} not found")

            return []
        transactions = []

        for line in file.read_text_file(self.store.history_file_path, True):
            transaction = Transaction.parse_line(self.store, line)
            if transaction:
                transactions.append(transaction)

        return transactions

    def _write_line(self, new_line: str) -> None:
        """Write a new line into the history file.
        :param new_line: The line to be added.
        :raise:
            :WriteFileError: Failed to update history file
        """
        try:
            empty = True
            if (
                self.store.history_file_path.is_file()
                and os.stat(os.fspath(self.store.history_file_path)).st_size != 0
            ):
                empty = False
            elif not self.store.admin_dir.is_dir():
                self.store.admin_dir.mkdir(parents=True)

            with self.store.history_file_path.open("ab+") as fph:
                if not empty:
                    # Ensure that newline character is present at the end of the file
                    nls = os.linesep.encode("utf-8")
                    fph.seek(-len(nls), os.SEEK_END)
                    if fph.read(len(nls)) != nls:
                        fph.write(nls)
                fph.write(new_line.encode("utf-8"))
        except OSError as exc:
            raise WriteFileError(self.store.history_file_path) from exc

    def reset(self) -> None:
        """Reset to the transactions list to `None`."""
        self.transactions_list = None

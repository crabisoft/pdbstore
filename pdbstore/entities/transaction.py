"""A single transaction of a symbol store."""

import re
from datetime import datetime

from pdbstore.entities.entry import TransactionEntry
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.exceptions import PDBStoreException
from pdbstore.typing import List, Optional, Protocol, Union

__all__ = ["Transaction", "TransactionBinding", "TransactionRegEx"]


class TransactionRegEx:
    """Constant related to transaction decryption"""

    # pylint: disable=too-few-public-methods
    TRANSACTION_PREFIX_RE = re.compile(r"(?P<id>\d+),(?P<type>add|del),(?P<tail>.*)")

    TRANSACTION_ADD_RE = re.compile(
        # pylint: disable=line-too-long
        r'(?P<ref>file|ptr),(?P<timestamp>(?:\d\d/\d\d/\d\d\d\d),(?:\d\d:\d\d:\d\d)),"(?P<product>[^"]*)","(?P<version>[^"]*)","(?P<comment>[^"]*)",.*'
    )

    TRANSACTION_DEL_RE = re.compile(r"(?P<id>\d+)")


class TransactionBinding(Protocol):
    """What a transaction needs from its store to resolve its own state.

    A committed transaction cannot answer questions such as "which files do I
    reference?" without reaching the store that holds it. Rather than letting
    the entity reach out itself, the store binds an implementation of this
    protocol to the transactions it hands out. The entity therefore stays free
    of any knowledge about how or where the data lives.
    """

    def load_entries(self, transaction: "Transaction") -> List[TransactionEntry]:
        """Load the entries referenced by ``transaction``."""

    def is_deleted(self, transaction: "Transaction") -> bool:
        """Determine whether ``transaction`` has been marked as deleted."""

    def is_promoted(self, transaction: "Transaction") -> bool:
        """Determine whether ``transaction`` has been marked as promoted."""


class Transaction:
    """A symbol store transaction."""

    def __init__(
        self,
        transaction_id: Union[str, None] = None,
        transaction_type: TransactionType = TransactionType.ADD,
        ref: str = "file",
        timestamp: Union[datetime, None] = None,
        product: Union[str, None] = None,
        version: Union[str, None] = None,
        comment: Union[str, None] = None,
        deleted_id: Union[str, None] = None,
        binding: Optional[TransactionBinding] = None,
    ):
        self.transactions_entries: List[TransactionEntry] = []
        self.transaction_id: str = transaction_id  # type: ignore[assignment]
        self.ref: str = ref
        self.timestamp: Union[datetime, None] = timestamp
        self.product: Union[str, None] = product
        self.version: Union[str, None] = version
        self.comment: Union[str, None] = comment
        self.deleted_id: Union[str, None] = deleted_id
        self.binding: Optional[TransactionBinding] = binding
        if isinstance(transaction_type, TransactionType):
            self.transaction_type: TransactionType = transaction_type
        elif transaction_type in [member.value for member in TransactionType]:
            self.transaction_type: TransactionType = TransactionType(  # type: ignore[no-redef]
                transaction_type
            )
        else:
            raise PDBStoreException(f"{transaction_type} : unsupported transaction type keyword")

    @property
    def id(self) -> str:  # pylint: disable=invalid-name
        """Retrieve transaction id

        :return: The transcaction id as a string formated using ``%010d`` format
        """
        return self.transaction_id

    def is_committed(self) -> bool:
        """Determine whether the transaction is committed or not

        :return: True if committed (as part of symbol store), else False
        """
        return self.transaction_id is not None

    def is_delete_operation(self) -> bool:
        """Determine whether the transaction is associated to a del operation.

        :return: True if it is a deleted transaction, else False."""
        return self.transaction_type == TransactionType.DEL

    def is_deleted(self) -> bool:
        """Determine whether the transaction is deleted or not

        :return: True if it is a deleted transaction, else False."""
        if self.is_delete_operation():
            return True
        if not self.is_committed() or self.binding is None:
            return False
        return self.binding.is_deleted(self)

    def is_promoted(self) -> bool:
        """Determine whether the transaction is promoted or not

        :return: True if it is a promoted transaction, else False."""
        if not self.is_committed() or self.binding is None:
            return False
        return self.binding.is_promoted(self)

    @property
    def entries(self) -> List[TransactionEntry]:
        """Retrieve the list of associated entries

        :return: List of associated
            :class:`TransactionEntry <pdbstore.entities.entry.TransactionEntry>` objects
        """
        if not self.transactions_entries and self.binding is not None and not self.is_deleted():
            self.transactions_entries = self.binding.load_entries(self)

        return self.transactions_entries

    @property
    def count(self) -> int:
        """Retrieve the total number of entries

        :return: The total number of registered entries
        """
        return len(self.entries)

    def add_entry(self, entry: TransactionEntry) -> None:
        """Add a new TransactionEntry object

        :param entry: The TransactionEntry object to be added
        """
        self.transactions_entries.append(entry)

    def find_entry(self, file_name: str, file_hash: str) -> Optional[TransactionEntry]:
        """Search a transaction entry given by file name and hash value.

        :param file_name: The file name to be found
        :param file_hash: The required file hash associated to `file_name`
        :return: The requested
            :class:`TransactionEntry <pdbstore.entities.entry.TransactionEntry>`
            object if successful, else None
        """
        for entry in self.entries:
            if entry.file_name == file_name and entry.file_hash == file_hash:
                return entry
        # Not found
        return None

    def mark_committed(self, transaction_id: str, timestamp: datetime) -> None:
        """Stamp the transaction with the identifier and date it was committed with.

        :param transaction_id: The allocated transaction identifier.
        :param timestamp: The transaction date/time.
        """
        self.transaction_id = transaction_id
        self.timestamp = timestamp

    def __str__(self) -> str:
        """Get transaction as a string

        :return: The string representation
        """
        if not self.is_committed():
            return ""

        if self.is_delete_operation():
            if not self.deleted_id:
                return ""
            return f"{self.transaction_id},{self.transaction_type.value},{self.deleted_id}"

        if not self.timestamp:
            return ""
        date_stamp = self.timestamp.strftime("%m/%d/%Y")
        time_stamp = self.timestamp.strftime("%H:%M:%S")

        # pylint: disable=line-too-long
        return f'{self.transaction_id},{self.transaction_type.value},{self.ref},{date_stamp},{time_stamp},"{self.product}","{self.version}","{self.comment}",'

    def __repr__(self) -> str:
        """Get text representation from a Transaction object."""
        return str(self)

    @staticmethod
    def parse_line(
        line: str, binding: Optional[TransactionBinding] = None
    ) -> Union["Transaction", None]:
        """Parse a transaction entry from a server or history file.

        :param line: the line to be parsed
        :param binding: Optional binding to attach to the created transaction.
        :return: The corresponding Transaction object if successful, else None
        """
        line_res = TransactionRegEx.TRANSACTION_PREFIX_RE.match(line)
        if not line_res:
            return None

        transaction_id = line_res.group("id")
        transaction_type = line_res.group("type")
        if transaction_type == TransactionType.ADD.value:
            add_res = TransactionRegEx.TRANSACTION_ADD_RE.match(line_res.group("tail"))
            if not add_res:
                return None

            timestamp = datetime.strptime(add_res.group("timestamp"), "%m/%d/%Y,%H:%M:%S")
            return Transaction(
                transaction_id,
                TransactionType.ADD,
                add_res.group("ref"),
                timestamp,
                add_res.group("product"),
                add_res.group("version"),
                add_res.group("comment"),
                binding=binding,
            )

        del_res = TransactionRegEx.TRANSACTION_DEL_RE.match(line_res.group("tail"))
        if not del_res:
            return None

        return Transaction(
            transaction_id,
            TransactionType.DEL,
            deleted_id=del_res.group("id"),
            binding=binding,
        )

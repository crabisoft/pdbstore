"""Queries run against the transactions of a symbol store.

These read-only operations are shared by several interactors, so they are
expressed once here rather than duplicated. They are plain functions because
they hold no state of their own beyond the gateway they are handed.
"""

from pdbstore.entities.entry import TransactionEntry
from pdbstore.entities.transaction import Transaction
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.exceptions import ImproperTransactionTypeError, TransactionNotFoundError
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import (
    Callable,
    Dict,
    Generator,
    List,
    Mapping,
    Optional,
    PathLike,
    Tuple,
    TypeVar,
    Union,
)
from pdbstore.usecases.gateways.symbol_file import SymbolFileReader
from pdbstore.usecases.gateways.symbol_store import SymbolStoreGateway

__all__ = [
    "FilesUsage",
    "build_entry",
    "fetch_symbol",
    "find_entries",
    "find_transaction",
    "iterate",
]


AnyTransaction = TypeVar("AnyTransaction", bound=Transaction)
"""Whichever transaction flavour the caller works with.

The compatibility layer hands out a subclass of
:class:`Transaction <pdbstore.entities.transaction.Transaction>`, and these
queries preserve that type rather than flattening it back to the base one.
"""


class FilesUsage:
    """Which transactions reference each stored file."""

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
        """Determine which files would become orphaned by deleting a transaction.

        A file referenced by a single transaction is only kept alive by that
        transaction, so removing it releases the file.

        :param transaction: The transaction about to be deleted.
        :return: The identifying pairs of the files that become unused.
        """
        deleted_entries = []

        for entry, ids in self.entries.items():
            if transaction.id in ids:
                if len(ids) == 1:
                    # The entry is used only by the input transaction
                    deleted_entries.append(entry)

        return deleted_entries


def find_transaction(
    transactions: Mapping[str, AnyTransaction],
    transaction_id: Union[str, int],
    transaction_type: Optional[TransactionType] = None,
) -> AnyTransaction:
    """Find a transaction given by its identifier.

    :param transactions: The known transactions, indexed by identifier.
    :param transaction_id: The transaction id.
    :param transaction_type: Optional expected transaction type.
    :return: The matching
        :class:`Transaction <pdbstore.entities.transaction.Transaction>` object.
    :raise:
        :TransactionNotFoundError: The specified transaction cannot be found.
        :ImproperTransactionTypeError: The transaction exists with another type.
    """
    trans_id = f"{int(transaction_id):010d}"
    PDBStoreOutput().debug(f"Finding ID ... {trans_id}")
    transaction = transactions.get(trans_id)
    if not transaction:
        raise TransactionNotFoundError(transaction_id)
    if transaction_type and transaction_type.value != transaction.transaction_type.value:
        raise ImproperTransactionTypeError(
            transaction_id,
            transaction.transaction_type.value,
            transaction_type.value,
        )
    return transaction


def build_entry(
    gateway: SymbolStoreGateway, reader: SymbolFileReader, file_path: PathLike
) -> Optional[TransactionEntry]:
    """Build the transaction entry a local file would be stored as.

    :param gateway: The symbol store to compute the entry against.
    :param reader: The reader identifying the input file.
    :param file_path: Path to the input file.
    :return: The :class:`TransactionEntry <pdbstore.entities.entry.TransactionEntry>`
        object if the signature could be computed, else None.
    :raise:
        :FileNotExistsError: The specified file doesn't exist.
        :UnknowFileTypeError: Unsupported file type.
    """
    file_hash = reader.signature_of(file_path)
    if not file_hash:
        return None

    file_name = TransactionEntry.file_name_of(file_path)
    return TransactionEntry(
        file_name,
        file_hash,
        file_path,
        gateway.is_entry_compressed(file_name, file_hash),
    )


def fetch_symbol(
    reader: SymbolFileReader,
    transactions: Mapping[str, AnyTransaction],
    file_path: PathLike,
) -> Optional[Tuple[AnyTransaction, TransactionEntry]]:
    """Find the symbol file matching a pe file.

    The debugging information carried by the pe file identifies the symbol file
    it was built with, which is then looked up in the store.

    :param reader: The reader extracting the debugging information.
    :param transactions: The known transactions, indexed by identifier.
    :param file_path: Path to the pe file.
    :return: The first matching transaction and entry, or None when the symbol
        file is not stored.
    """
    dbg_info = reader.debug_info_of(file_path)
    if not dbg_info:
        return None

    # Search the first transaction where the file is referenced
    for transaction in transactions.values():
        for entry in transaction.entries:
            if (entry.file_name, entry.file_hash) == dbg_info:
                return (transaction, entry)

    # Not found
    return None


def find_entries(
    gateway: SymbolStoreGateway,
    reader: SymbolFileReader,
    transactions: Mapping[str, AnyTransaction],
    file_path: PathLike,
    full: Optional[bool] = False,
) -> List[Tuple[AnyTransaction, TransactionEntry]]:
    """Find the transactions referencing a given file.

    :param gateway: The symbol store to search.
    :param reader: The reader identifying the requested file.
    :param transactions: The known transactions, indexed by identifier.
    :param file_path: Path to the requested file.
    :param full: True to report every referencing transaction, False to stop at
        the first one of each.
    :return: The matching transaction and entry pairs.
    """
    entries_list: List[Tuple[AnyTransaction, TransactionEntry]] = []

    file_entry = build_entry(gateway, reader, file_path)
    if not file_entry:
        PDBStoreOutput().debug(f"failed to create transaction entry from {file_path} file")
        return entries_list

    for transaction in transactions.values():
        for entry in transaction.entries:
            if (entry.file_name, entry.file_hash) == (
                file_entry.file_name,
                file_entry.file_hash,
            ):
                entries_list.append((transaction, entry))
                if not full:
                    break

    return entries_list


def iterate(
    transactions: Mapping[str, AnyTransaction],
    filter_cb: Optional[Callable[[AnyTransaction], bool]] = None,
) -> Generator[Tuple[AnyTransaction, TransactionEntry], None, None]:
    """Iterate over every transaction and the entries it references.

    :param transactions: The known transactions, indexed by identifier.
    :param filter_cb: Optional callback filtering the transactions to visit.
    """
    for transaction in transactions.values():
        if not filter_cb or filter_cb(transaction):
            for entry in transaction.entries:
                yield (transaction, entry)


def files_usage(transactions: Mapping[str, Transaction]) -> FilesUsage:
    """Build the file usage map out of the known transactions.

    :param transactions: The known transactions, indexed by identifier.
    :return: The :class:`FilesUsage` describing which transaction uses what.
    """
    usage = FilesUsage()
    for transaction in transactions.values():
        for entry in transaction.entries:
            usage.add_entry(entry, transaction)
    return usage

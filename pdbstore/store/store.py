"""Store-bound entry point.

.. deprecated::
    A symbol store is now reached through a
    :class:`SymbolStoreGateway <pdbstore.usecases.gateways.symbol_store.SymbolStoreGateway>`
    and driven by the interactors of :mod:`pdbstore.usecases`. This class keeps
    the historical API by assembling that graph itself and delegating to it.

    New code should call :func:`pdbstore.factory.open_store` and use
    the interactors directly, which is what makes it work against any backend.
    The path-shaped members here — ``rootdir``, ``admin_dir`` and the
    ``*_file_path`` properties — only mean something for a store held on a
    local filesystem.
"""

from pathlib import Path

from pdbstore.adapters.symsrv.gateway import SymSrvGateway
from pdbstore.drivers.blob.factory import create_blob_store
from pdbstore.drivers.compression.cab import CabCompressor
from pdbstore.drivers.parsing.reader import PdbSymbolFileReader
from pdbstore.entities import symsrv_layout
from pdbstore.entities.summary import Summary
from pdbstore.entities.transaction import Transaction as _Transaction
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.store.entry import TransactionEntry
from pdbstore.store.history import History
from pdbstore.store.transaction import Transaction
from pdbstore.store.transactions import Transactions
from pdbstore.typing import (
    Callable,
    cast,
    Dict,
    Generator,
    List,
    Optional,
    PathLike,
    Tuple,
    Union,
)
from pdbstore.usecases import lookup
from pdbstore.usecases.commit import CommitTransactionInteractor
from pdbstore.usecases.delete import (
    CleanOldVersionsInteractor,
    DeleteTransactionInteractor,
)
from pdbstore.usecases.promote import PromoteTransactionInteractor
from pdbstore.usecases.store_state import StoreState

__all__ = ["Store"]


class _BoundStoreState(StoreState):
    """Working set handing out store-bound transactions.

    The interactors are happy with plain entities, but the historical API
    promises transactions that know their store, so they are bound as they are
    loaded rather than wrapped at every call site.
    """

    def __init__(self, gateway: SymSrvGateway, store: "Store"):
        super().__init__(gateway, PdbSymbolFileReader())
        self._store = store

    @property
    def transactions(self) -> Dict[str, _Transaction]:
        """Retrieve the active transactions, bound to their store."""
        if not self._transactions:
            self._transactions = {
                key: Transaction.of(self._store, value)
                for key, value in self.gateway.load_transactions().items()
            }
        return self._transactions

    @property
    def history(self) -> List[_Transaction]:
        """Retrieve the full history, bound to its store."""
        if self._history is None:
            self._history = [
                Transaction.of(self._store, item) for item in self.gateway.load_history()
            ]
        return self._history

    @property
    def bound_transactions(self) -> Dict[str, Transaction]:
        """Retrieve the active transactions as store-bound objects.

        Every value is built by :meth:`Transaction.of`, so the narrowing is
        sound; it is simply not expressible while ``Dict`` stays invariant.
        """
        return cast(Dict[str, Transaction], self.transactions)

    def register(self, transaction: _Transaction) -> None:
        """Record a freshly committed transaction, bound to its store."""
        super().register(Transaction.of(self._store, transaction))


class Store:
    """Manage symbol store."""

    def __init__(self, store_path: PathLike):
        self.gateway: SymSrvGateway = SymSrvGateway(create_blob_store(store_path), CabCompressor())
        self.state: _BoundStoreState = _BoundStoreState(self.gateway, self)
        self.transactions: Transactions = Transactions(self)
        self.history: History = History(self)

    def path_of(self, key: str) -> Path:
        """Resolve a store key into a local path.

        :param key: The key to be resolved.
        :return: The local path of ``key``.
        """
        local = self.gateway.blob.local_path(key)
        if local is not None:
            return local
        return Path(self.gateway.location).joinpath(*symsrv_layout.split_key(key))

    @property
    def rootdir(self) -> Path:
        """Retrieve the root directory of the symbol store."""
        return self.path_of("")

    @property
    def admin_dir(self) -> Path:
        """Retrieve the full path name of 000Admin directory"""
        return self.path_of(symsrv_layout.admin_key())

    @property
    def last_id_file_path(self) -> Path:
        """Retrieve the full path name of lastid.txt"""
        return self.path_of(symsrv_layout.lastid_key())

    @property
    def history_file_path(self) -> Path:
        """Retrieve the full path name of history.txt"""
        return self.path_of(symsrv_layout.history_key())

    @property
    def server_file_path(self) -> Path:
        """Retrieve the full path name of server.txt"""
        return self.path_of(symsrv_layout.server_key())

    @property
    def pingme_file_path(self) -> Path:
        """Retrieve the full path name of pingme.txt"""
        return self.path_of(symsrv_layout.pingme_key())

    @property
    def next_transaction_id(self) -> str:
        """Generate next valid transaction id

        :return: The next transaction id
        :raise:
            :ReadFileError: Failed to read lastid file
            :UnexpectedError: Failed to convert read string into an integer
        """
        return self.gateway.next_transaction_id

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
        self, transaction_id: Union[str, int], transaction_type: Optional[TransactionType] = None
    ) -> Transaction:
        """Find an existing transaction given by its id

        :param transaction_id: The transaction id.
        :param transaction_type: Optional transaction type.
        :return: A :class:`Transaction <pdbstore.store.transaction.Transaction>` object
        :raise:
            :TransactionNotFoundError: The specified transition cannot be found.
            :ImproperTransactionTypeError: The specified transition exists but with
                                           a different transaction type.
        """
        return lookup.find_transaction(
            self.state.bound_transactions, transaction_id, transaction_type
        )

    def delete_transaction(self, transaction_id: Union[str, int], dry_run: bool = False) -> Summary:
        """Delete an existing transaction given by its id

        :param transaction_id: The transaction id to be deleted.
        :param dry_run: True to just print the list of files to be deleted.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object
        :raise:
            :TransactionNotFoundError: The specified transition cannot be found.
            :ImproperTransactionTypeError: The specified transition exists but with
                a different transaction type.
            :WriteFileError: An error occurs when updating global file.
        """
        return DeleteTransactionInteractor(self.state).execute(transaction_id, dry_run)

    def commit(
        self,
        transaction: Transaction,
        force: Optional[bool] = False,
        store: Optional["Store"] = None,
    ) -> Summary:
        """Commit a transaction into the store.

        :param transaction: The transaction to be committed.
        :param force: True to overwrite files already present in the store.
        :param store: Optional source :class:`Store <pdbstore.store.store.Store>`
            to promote the files from.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object
        :raise:
            :UnexpectedError: Failed to create missing directories or update
                              global files
            :WriteFileError: An error occurs when updating a file
            :ReadFileError: Failed to read lastid file
        """
        return CommitTransactionInteractor(self.state).execute(
            transaction, force, store.gateway if store is not None else None
        )

    def fetch_symbol(self, file_path: PathLike) -> Optional[Tuple[Transaction, TransactionEntry]]:
        """Fetch pdb file given an executable file.

        :param file_path: Path to the pe file
        :return: The matching transaction and entry if successful, else None.
        """
        return lookup.fetch_symbol(  # type: ignore[return-value]
            self.state.reader, self.state.bound_transactions, file_path
        )

    def find_entries(
        self, file_path: PathLike, full: Optional[bool] = False
    ) -> List[Tuple[Transaction, TransactionEntry]]:
        """Find a transaction entry given by a file path

        :param file_path: Path to the request file
        :param full: True to retrieve all transaction entries associated
                     to `file_path`, else False to retrieve only the
                     first transaction entry.
        :return: A list of associated transaction entries.
        """
        return lookup.find_entries(  # type: ignore[return-value]
            self.gateway, self.state.reader, self.state.bound_transactions, file_path, full
        )

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
        :param comment: Optional comment to filter the transactions to be deleted.
        :param dry_run: True to just print the list of transactions id to be deleted.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object
        """
        return CleanOldVersionsInteractor(self.state).execute(
            product, version, keep, comment, dry_run
        )

    def iterator(
        self, filter_cb: Optional[Callable[[Transaction], bool]] = None
    ) -> Generator[Tuple[Transaction, TransactionEntry], None, None]:
        """Iterate over all transactions and file entries.

        :param filter_cb: Optional callback function to filter transactions.
        """
        return lookup.iterate(  # type: ignore[return-value]
            self.state.bound_transactions, filter_cb
        )

    def promote_transaction(
        self, transaction: Optional[Transaction], comment: Optional[str] = None
    ) -> Summary:
        """Copy an existing transaction from another store.

        :param transaction: The :class:`Transaction <pdbstore.store.transaction.Transaction>`
            object to be copied.
        :param comment: Optional comment for the newly created transaction.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object
        """
        source = transaction.store.gateway if transaction is not None else self.gateway
        return PromoteTransactionInteractor(self.state).execute(transaction, source, comment)

    def check_admin_dir(self) -> None:
        """Check that all required directories exists"""
        self.gateway.prepare()

    def reset(self) -> None:
        """Reset to an empty store from memory only."""
        self.state.reset()

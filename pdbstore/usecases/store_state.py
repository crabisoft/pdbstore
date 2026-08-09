"""In-memory working set of a symbol store.

Loading the transaction listing costs a full read of ``server.txt``, and the
interactors need it repeatedly within a single command. This holds that working
set, loaded on first use and shared by the interactors operating on the same
store, so a command reads the listing once whatever it ends up doing with it.
"""

from pdbstore.entities.transaction import Transaction
from pdbstore.typing import Dict, List, Optional
from pdbstore.usecases.gateways.symbol_file import SymbolFileReader
from pdbstore.usecases.gateways.symbol_store import SymbolStoreGateway

__all__ = ["StoreState"]


class StoreState:
    """Cache the transactions and history of one symbol store.

    Also carries the symbol file reader, so that an interactor needing to
    identify an input file has it at hand without every call site threading it
    through.
    """

    def __init__(self, gateway: SymbolStoreGateway, reader: SymbolFileReader):
        self.gateway: SymbolStoreGateway = gateway
        self.reader: SymbolFileReader = reader
        self._transactions: Optional[Dict[str, Transaction]] = None
        self._history: Optional[List[Transaction]] = None

    @property
    def transactions(self) -> Dict[str, Transaction]:
        """Retrieve the active transactions, indexed by identifier.

        :return: The transactions listed by the store.
        :raise:
            :ReadFileError: The transaction listing cannot be read.
        """
        if not self._transactions:
            self._transactions = self.gateway.load_transactions()
        return self._transactions

    @property
    def history(self) -> List[Transaction]:
        """Retrieve the full history, including delete operations.

        :return: The transactions in chronological order.
        :raise:
            :ReadFileError: The history cannot be read.
        """
        if self._history is None:
            self._history = self.gateway.load_history()
        return self._history

    def register(self, transaction: Transaction) -> None:
        """Record a freshly committed transaction in the working set.

        :param transaction: The transaction that was just committed.
        """
        self.transactions[transaction.transaction_id] = transaction
        if self._history is not None:
            self._history.append(transaction)

    def forget(self, transaction: Transaction) -> None:
        """Drop a deleted transaction from the working set.

        :param transaction: The transaction that was just deleted.
        """
        self.transactions.pop(transaction.id, None)

    def remember_history(self, transaction: Transaction) -> None:
        """Record a transaction in the history working set only.

        :param transaction: The transaction to be recorded.
        """
        if self._history is not None:
            self._history.append(transaction)

    def reset(self) -> None:
        """Drop the working set, forcing a reload on next access."""
        self._transactions = None
        self._history = None
        self.gateway.reset()

"""Historical symbol store API.

.. deprecated::
    This package is a compatibility layer. The symbol store is now described by
    the entities of :mod:`pdbstore.entities`, driven by the interactors of
    :mod:`pdbstore.usecases`, and reached through the gateways of
    :mod:`pdbstore.usecases.gateways`.

    The classes below keep the previous API working — including the
    path-shaped members that only apply to a store held on a local filesystem —
    by assembling that graph and delegating to it.
"""

from pdbstore.entities.summary import OpStatus, Summary
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.store.entry import TransactionEntry
from pdbstore.store.history import History
from pdbstore.store.store import Store
from pdbstore.store.transaction import Transaction
from pdbstore.store.transactions import Transactions

__all__ = [
    "History",
    "OpStatus",
    "Store",
    "Summary",
    "Transaction",
    "TransactionEntry",
    "TransactionType",
    "Transactions",
]

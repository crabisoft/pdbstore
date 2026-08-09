"""Gateways through which the interactors reach the outside world.

An interface is declared where it is consumed, so both gateways live in the
use case layer and are implemented further out — by
:mod:`pdbstore.adapters` for the symbol store, by :mod:`pdbstore.drivers` for
the blob store.

Two gateways rather than one, because the storage administration interactors
under :mod:`pdbstore.usecases.storage` genuinely work in terms of keys: for a
migration, the blob store *is* the subject matter. Every other interactor is
barred from importing :class:`BlobStore`, and the layering rules enforce it.
"""

from pdbstore.usecases.gateways.blob_store import BlobStat, BlobStore
from pdbstore.usecases.gateways.symbol_store import SymbolStoreGateway

__all__ = [
    "BlobStat",
    "BlobStore",
    "SymbolStoreGateway",
]

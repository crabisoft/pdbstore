"""Assembling a usable symbol store out of a location.

This is the composition root: the single spot allowed to know every layer at
once, because building the object graph is exactly what it is for. Everything
else receives its dependencies already wired and stays unaware of which backend
ended up behind them.
"""

from pdbstore.adapters.symsrv.gateway import SymSrvGateway
from pdbstore.drivers.blob.factory import create_blob_store
from pdbstore.drivers.compression.cab import CabCompressor
from pdbstore.drivers.parsing.reader import PdbSymbolFileReader
from pdbstore.typing import PathLike
from pdbstore.usecases.gateways.symbol_store import SymbolStoreGateway
from pdbstore.usecases.store_state import StoreState

__all__ = ["open_store", "open_symbol_store"]


def open_symbol_store(location: PathLike) -> SymbolStoreGateway:
    """Build the symbol store gateway serving a location.

    :param location: A local directory path, or a URI such as
        ``file:///var/symbols``.
    :return: The gateway serving ``location``.
    :raise:
        :PDBStoreException: The URI scheme has no registered backend.
    """
    return SymSrvGateway(create_blob_store(location), CabCompressor())


def open_store(location: PathLike) -> StoreState:
    """Build the working set of the symbol store serving a location.

    :param location: A local directory path, or a URI such as
        ``file:///var/symbols``.
    :return: The :class:`StoreState <pdbstore.usecases.store_state.StoreState>`
        the interactors operate on.
    :raise:
        :PDBStoreException: The URI scheme has no registered backend.
    """
    return StoreState(open_symbol_store(location), PdbSymbolFileReader())

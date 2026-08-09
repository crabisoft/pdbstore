"""Interface adapters.

This layer converts between the shape the interactors work with and the shape
the outside world expects. It holds the implementation of
:class:`SymbolStoreGateway <pdbstore.usecases.gateways.symbol_store.SymbolStoreGateway>`
and, historically, the command line controllers and presenters that still live
under :mod:`pdbstore.cli`.
"""

from pdbstore.adapters.symsrv import SymSrvGateway

__all__ = ["SymSrvGateway"]

""" Define list of supported transaction types.

.. deprecated::
    Moved to :mod:`pdbstore.entities.transaction_type`. This module re-exports
    it so that existing imports keep working.
"""

from pdbstore.entities.transaction_type import TransactionType

__all__ = ["TransactionType"]

"""Per-transaction statistics.

.. deprecated::
    Moved to :mod:`pdbstore.usecases.statistics.transaction`. This module
    re-exports them so that existing imports keep working.
"""

from pdbstore.usecases.statistics.transaction import (
    TransactionEntryStatistics,
    TransactionStatistics,
)

__all__ = ["TransactionEntryStatistics", "TransactionStatistics"]

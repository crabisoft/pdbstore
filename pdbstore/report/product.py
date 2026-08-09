"""Per-product statistics.

.. deprecated::
    Moved to :mod:`pdbstore.usecases.statistics.product`. This module
    re-exports them so that existing imports keep working.
"""

from pdbstore.usecases.statistics.product import (
    ProductEntryStatistics,
    ProductStatistics,
)

__all__ = ["ProductEntryStatistics", "ProductStatistics"]

"""Statistics base classes.

.. deprecated::
    Moved to :mod:`pdbstore.usecases.statistics.base`. This module re-exports
    them so that existing imports keep working.
"""

from pdbstore.usecases.statistics.base import (
    BaseEntryStatistics,
    BaseStatistics,
    Statistics,
)

__all__ = ["BaseEntryStatistics", "BaseStatistics", "Statistics"]

"""Per-file statistics.

.. deprecated::
    Moved to :mod:`pdbstore.usecases.statistics.file`. This module re-exports
    them so that existing imports keep working.
"""

from pdbstore.usecases.statistics.file import FileEntryStatistics, FileStatistics

__all__ = ["FileEntryStatistics", "FileStatistics"]

"""Operation summaries.

.. deprecated::
    Moved to :mod:`pdbstore.entities.summary`. This module re-exports it so
    that existing imports keep working.
"""

from pdbstore.entities.summary import OpStatus, Summary

__all__ = ["Summary", "OpStatus"]

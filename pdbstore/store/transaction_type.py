""" Define list of supported transaction types.
"""

from enum import Enum

__all__ = ["TransactionType"]


class TransactionType(Enum):
    """List of predefined transaction types."""

    ADD = "add"
    """Add a new transaction"""
    DEL = "del"
    """ Delete an existing transaction"""
    QUERY = "query"
    """ Query files from symbol store"""
    FETCH = "fetch"
    """ Search and extract files from symbol store"""

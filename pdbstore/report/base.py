from abc import ABC, abstractmethod

from pdbstore.store import Store
from pdbstore.typing import List, Mapping, Tuple


class BaseEntryStatistics(ABC):
    """Handle statistic for one specific entry."""

    def __init__(self) -> None:
        self.trans_count: int = 1

    def get_transactions_count(self) -> int:
        """Retrieve the total number of associated transactions."""
        return self.trans_count

    @property
    @abstractmethod
    def resources(self) -> List[str]:
        """List of data member containing statistics information from derived class."""


Statistics = Mapping[Tuple[str, str], BaseEntryStatistics]


class BaseStatistics(ABC):
    """Base class form managing statistics."""

    @property
    @abstractmethod
    def statistics(self) -> Statistics:
        """The data member containing all generated statistics."""

    @property
    @abstractmethod
    def key1(self) -> str:
        """The first collecting criteria"""

    @property
    @abstractmethod
    def key2(self) -> str:
        """The second collecting criteria"""

    @property
    @abstractmethod
    def value1(self) -> str:
        """The first collected data"""

    @property
    @abstractmethod
    def value2(self) -> str:
        """The second collected data"""

    @abstractmethod
    def build(self, store: Store) -> bool:
        """Build required statistics dictonary

        :param store: The symbol store to analyze
        :return: True if successful, else False
        """
        return False

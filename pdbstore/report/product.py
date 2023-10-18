from collections import OrderedDict

from pdbstore.report.base import BaseEntryStatistics, BaseStatistics
from pdbstore.store import Store, Transaction
from pdbstore.typing import Dict, List, Optional, Tuple

__all__ = ["ProductStatistics"]


class ProductEntryStatistics(BaseEntryStatistics):
    """Handle statistic for one product."""

    resources: List[str] = ["files_count", "disk_space", "shared_space"]

    def __init__(
        self, transaction_id: str, files_count: int, disk_space: int, shared_space: int
    ) -> None:
        self.transaction_id = transaction_id
        self.files_count: int = files_count
        self.disk_space: int = disk_space
        self.shared_space: int = shared_space
        super().__init__()

    def get_files_count(self) -> int:
        """Retrieve the total number of associated files."""
        return self.files_count

    def get_disk_space(self) -> int:
        """Retrieve the size of disk space allocated to the product only."""
        return self.disk_space

    def get_shared_space(self) -> int:
        """Retrieve the total size of disk space shared with other products."""
        return self.shared_space


class ProductStatistics(BaseStatistics):
    """Handle statistics for a specific file or product name/version."""

    key1: str = "Product name"
    key2: str = "Product version"
    value1: str = "File count"
    value2: str = "Disk space"
    statistics: Dict[Tuple[str, str], ProductEntryStatistics] = {}

    def build(self, store: Store) -> bool:
        """Build required statistics dictonary

        :param store: The symbol store to analyze
        :return: True if successful, else False
        """
        files_reported: List[Tuple[str, str]] = []
        for transaction in store.transactions.transactions.values():
            if transaction.product and not transaction.is_deleted():
                disk_space = 0
                shared_space = 0
                for entry in transaction.entries:
                    key = (entry.file_name, entry.file_hash)
                    if key not in files_reported:
                        files_reported.append(key)
                        disk_space += entry.get_disk_usage()
                    else:
                        shared_space += entry.get_disk_usage()
                self._add(transaction, disk_space, shared_space)
        self.statistics = OrderedDict(
            (key, value)
            for key, value in sorted(
                self.statistics.items(), reverse=True, key=lambda x: x[1].transaction_id
            )
        )
        return True

    def _add(
        self,
        transaction: Transaction,
        disk_usage: int,
        shared_space: int,
    ) -> None:
        """Register a new entry given by a key with the associated disk space"""
        if not transaction.product:
            return
        key = (transaction.product, transaction.version or "undefined")
        entry: Optional[ProductEntryStatistics] = self.statistics.get(key)
        if entry:
            entry.trans_count += 1
            entry.files_count += transaction.count
            entry.disk_space += disk_usage
            entry.shared_space += shared_space
            entry.transaction_id = transaction.id
        else:
            self.statistics[key] = ProductEntryStatistics(
                transaction.id, transaction.count, disk_usage, shared_space
            )

from pdbstore.report.base import BaseEntryStatistics, BaseStatistics
from pdbstore.store import Store, Transaction
from pdbstore.typing import Dict, List, Tuple

__all__ = ["FileStatistics"]


class FileEntryStatistics(BaseEntryStatistics):
    """Handle statistic for a stored file."""

    resources: List[str] = ["product", "version", "count", "file_size"]

    def __init__(self, file_size: int) -> None:
        self.products_info: Dict[Tuple[str, str], int] = {}
        self.file_size: int = file_size
        super().__init__()

    def get_products(self) -> Dict[Tuple[str, str], int]:
        """Retrieve the product name/version dictionary usage."""
        return self.products_info

    def get_file_size(self) -> int:
        """Retrieve the assocaited file size."""
        return self.file_size

    def update(self, transaction: Transaction) -> None:
        """Update list of registered product for a given transaction"""
        if not transaction.product:
            return
        key = (transaction.product, transaction.version or "undefined")
        if key not in self.products_info:
            self.products_info[key] = 1
        else:
            self.products_info[key] += 1


class FileStatistics(BaseStatistics):
    """Handle statistics for a specific file or product name/version."""

    key1: str = "File name"
    key2: str = "File hash"
    value1: str = "File count"
    value2: str = "Disk space"
    statistics: Dict[Tuple[str, str], FileEntryStatistics] = {}

    def build(self, store: Store) -> bool:
        """Build required statistics dictonary

        :param store: The symbol store to analyze
        :return: True if successful, else False
        """
        file_usage = store.transactions.get_files_usage()
        if not file_usage:
            return True  # Empty store

        prev_key = None
        for file_key, tids in sorted(file_usage.entries.items(), key=lambda k: k[0]):
            if prev_key is None or prev_key != file_key:
                fes = FileEntryStatistics(0)
                prev_key = file_key
                self.statistics[file_key] = fes

            for trans_id in tids:
                transaction = store.transactions.find(trans_id)
                if transaction and not transaction.is_deleted():
                    if fes.get_file_size() == 0:
                        entry = transaction.find_entry(file_key[0], file_key[1])
                        if entry:
                            fes.file_size = entry.get_disk_usage()
                    fes.update(transaction)
        return True

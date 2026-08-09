"""Statistics collected per stored file."""

from pdbstore.entities.transaction import Transaction
from pdbstore.typing import Dict, List, Tuple
from pdbstore.usecases import lookup
from pdbstore.usecases.statistics.base import BaseEntryStatistics, BaseStatistics
from pdbstore.usecases.store_state import StoreState

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

    def build(self, state: StoreState) -> bool:
        """Build required statistics dictonary

        :param state: The working set of the symbol store to analyze
        :return: True if successful, else False
        """
        file_usage = lookup.files_usage(state.transactions)
        if not file_usage:
            return True  # Empty store

        prev_key = None
        for file_key, tids in sorted(file_usage.entries.items(), key=lambda k: k[0]):
            if prev_key is None or prev_key != file_key:
                fes = FileEntryStatistics(0)
                prev_key = file_key
                self.statistics[file_key] = fes

            for trans_id in tids:
                transaction = state.transactions.get(trans_id)
                if transaction and not transaction.is_deleted():
                    if fes.get_file_size() == 0:
                        entry = transaction.find_entry(file_key[0], file_key[1])
                        if entry:
                            stat = state.gateway.entry_stat(entry)
                            fes.file_size = stat.size if stat else 0
                    fes.update(transaction)
        return True

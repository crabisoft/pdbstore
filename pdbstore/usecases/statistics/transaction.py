"""Statistics collected per transaction."""

from pdbstore.entities.transaction import Transaction
from pdbstore.typing import Dict, List, Optional, Tuple, Union
from pdbstore.usecases.statistics.base import BaseEntryStatistics, BaseStatistics
from pdbstore.usecases.store_state import StoreState

__all__ = ["TransactionStatistics"]


class TransactionEntryStatistics(BaseEntryStatistics):
    """Handle statistic for one transaction."""

    resources: List[str] = [
        "files_count",
        "disk_space",
        "shared_space",
        "status",
        "files",
    ]

    def __init__(
        self,
        product: Optional[str],
        version: Optional[str],
        files_count: int,
        disk_space: int,
        shared_space: int,
        status: str = "active",
        files: Optional[List[Dict[str, Union[str, int, bool]]]] = None,
    ) -> None:
        self.product = product
        self.version = version
        self.files_count: int = files_count
        self.disk_space: int = disk_space
        self.shared_space: int = shared_space
        self.status: str = status
        self.files: Optional[List[Dict[str, Union[str, int, bool]]]] = files
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

    def get_status(self) -> str:
        """Retrieve the transaction status."""
        return self.status


class TransactionStatistics(BaseStatistics):
    """Handle statistics for a specific file or product name/version."""

    key1: str = "Transaction id"
    key2: str = "Transaction count"
    value1: str = "File count"
    value2: str = "Disk space"
    statistics: Dict[Tuple[str, str], TransactionEntryStatistics] = {}

    def build(self, state: StoreState) -> bool:
        """Build required statistics dictonary

        :param state: The working set of the symbol store to analyze
        :return: True if successful, else False
        """
        files_reported: List[Tuple[str, str]] = []
        for transaction in state.history:
            disk_space = 0
            shared_space = 0
            files: List[Dict[str, Union[str, int, bool]]] = []
            if transaction.product and not transaction.is_deleted():
                for entry in transaction.entries:
                    key = (entry.file_name, entry.file_hash)
                    stat = state.gateway.entry_stat(entry)
                    file_size = stat.size if stat else 0
                    files.append(
                        {
                            "path": str(entry.file_path),
                            "shared": key not in files_reported,
                            "size": file_size,
                        }
                    )
                    files.append(
                        {
                            "path": str(entry.file_path),
                            "shared": key not in files_reported,
                            "size": file_size,
                        }
                    )
                    if key not in files_reported:
                        files_reported.append(key)
                        disk_space += file_size
                    else:
                        shared_space += file_size

            self._add(transaction, disk_space, shared_space, files)
        return True

    def _add(
        self,
        transaction: Transaction,
        disk_usage: int,
        shared_space: int,
        files: List[Dict[str, Union[str, int, bool]]],
    ) -> None:
        """Register a new entry given by a key with the associated disk space"""
        key = (transaction.id, str(transaction.count))
        entry: Optional[TransactionEntryStatistics] = self.statistics.get(key)
        if transaction.is_delete_operation():
            return
        if entry:
            entry.trans_count += 1
            entry.files_count += transaction.count
            entry.disk_space += disk_usage
            entry.shared_space += shared_space
        else:
            self.statistics[key] = TransactionEntryStatistics(
                transaction.product,
                transaction.version,
                transaction.count,
                disk_usage,
                shared_space,
                "deleted" if transaction.is_deleted() else "active",
                files,
            )

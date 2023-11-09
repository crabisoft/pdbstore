from typing import Callable

from pdbstore.io.output import PDBStoreOutput
from pdbstore.report.base import BaseStatistics
from pdbstore.report.file import FileStatistics
from pdbstore.report.product import ProductStatistics
from pdbstore.report.transaction import TransactionStatistics
from pdbstore.store import Store
from pdbstore.typing import Dict, List, Optional

__all__ = ["ReportGenerator"]


class ReportGenerator:
    """Manage symbol store usage analysis data."""

    PRODUCTS = "products"
    FILES = "files"
    TRANSACTIONS = "transactions"

    def __init__(self, store: Store) -> None:
        self.store: Store = store
        self.mapping: Dict[str, Callable[[], BaseStatistics]] = {
            self.PRODUCTS: ProductStatistics,
            self.FILES: FileStatistics,
            self.TRANSACTIONS: TransactionStatistics,
        }

    def generate(self, report_type: str = "products") -> Optional["BaseStatistics"]:
        """generate symbol store statistics given a report type

        :param report_type: Specify which kind of report must be generated. It can
                            be `products` or `files`
        :return: The generated statistics if successsful, else None
        """
        if report_type not in self.mapping:
            PDBStoreOutput().error(f"{report_type} : unsupported report type")
            return None

        data = self.mapping[report_type]()
        if not data.build(self.store):
            return None  # pragma: no cover
        return data

    def supported_list(self) -> List[str]:
        """Retrieve the list of supported report types"""
        return list(self.mapping.keys())

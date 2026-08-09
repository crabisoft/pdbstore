"""Generate usage reports over a symbol store."""

from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import Callable, Dict, List, Optional
from pdbstore.usecases.statistics.base import BaseStatistics
from pdbstore.usecases.statistics.file import FileStatistics
from pdbstore.usecases.statistics.product import ProductStatistics
from pdbstore.usecases.statistics.transaction import TransactionStatistics
from pdbstore.usecases.store_state import StoreState

__all__ = ["GenerateReportInteractor"]


class GenerateReportInteractor:
    """Collect the statistics backing one kind of report."""

    PRODUCTS = "products"
    FILES = "files"
    TRANSACTIONS = "transactions"

    def __init__(self, state: StoreState) -> None:
        self.state: StoreState = state
        self.mapping: Dict[str, Callable[[], BaseStatistics]] = {
            self.PRODUCTS: ProductStatistics,
            self.FILES: FileStatistics,
            self.TRANSACTIONS: TransactionStatistics,
        }

    def execute(self, report_type: str = "products") -> Optional[BaseStatistics]:
        """Collect the statistics of a report.

        :param report_type: Which report to build. It can be ``products``,
            ``files`` or ``transactions``.
        :return: The collected statistics if successful, else None.
        """
        if report_type not in self.mapping:
            PDBStoreOutput().error(f"{report_type} : unsupported report type")
            return None

        data = self.mapping[report_type]()
        if not data.build(self.state):
            return None  # pragma: no cover
        return data

    def supported_list(self) -> List[str]:
        """Retrieve the list of supported report types"""
        return list(self.mapping.keys())

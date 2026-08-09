"""Report generation.

.. deprecated::
    The statistics are now collected by
    :class:`GenerateReportInteractor <pdbstore.usecases.report.GenerateReportInteractor>`.
    This class keeps the historical API by delegating to it.
"""

from pdbstore.typing import Any, cast, List, Optional, Union
from pdbstore.usecases.report import GenerateReportInteractor
from pdbstore.usecases.statistics.base import BaseStatistics
from pdbstore.usecases.store_state import StoreState

__all__ = ["ReportGenerator"]


class ReportGenerator:
    """Manage symbol store usage analysis data."""

    PRODUCTS = GenerateReportInteractor.PRODUCTS
    FILES = GenerateReportInteractor.FILES
    TRANSACTIONS = GenerateReportInteractor.TRANSACTIONS

    def __init__(self, store: Union[StoreState, Any]) -> None:
        self.store = store
        self._interactor = GenerateReportInteractor(_state_of(store))

    @property
    def mapping(self) -> Any:
        """Retrieve the supported report types and their builder."""
        return self._interactor.mapping

    def generate(self, report_type: str = "products") -> Optional[BaseStatistics]:
        """generate symbol store statistics given a report type

        :param report_type: Specify which kind of report must be generated. It can
                            be `products`, `files` or `transactions`
        :return: The generated statistics if successsful, else None
        """
        return self._interactor.execute(report_type)

    def supported_list(self) -> List[str]:
        """Retrieve the list of supported report types"""
        return self._interactor.supported_list()


def _state_of(store: Union[StoreState, Any]) -> StoreState:
    """Accept either a working set or a historical Store object."""
    if isinstance(store, StoreState):
        return store
    return cast(StoreState, store.state)

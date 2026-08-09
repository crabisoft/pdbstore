"""Check whether files are indexed by a symbol store."""

from pdbstore import util
from pdbstore.entities.summary import OpStatus, Summary
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.exceptions import (
    FileNotExistsError,
    PDBStoreException,
    UnknowFileTypeError,
)
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import Any, List, Optional, PathLike
from pdbstore.usecases import lookup
from pdbstore.usecases.store_state import StoreState

__all__ = ["QuerySymbolsInteractor"]


class QuerySymbolsInteractor:
    """Report whether each input file is already indexed."""

    def __init__(self, state: StoreState):
        self.state = state

    def execute(self, files: List[PathLike]) -> Summary:
        """Look every input file up in the store.

        :param files: The files to be looked up.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object.
        """
        output = PDBStoreOutput()
        gateway = self.state.gateway
        summary = Summary(None, OpStatus.SUCCESS, TransactionType.QUERY)

        output.verbose(f"Query record for {len(files)} file(s)")

        for file_path in files:
            try:
                entries = lookup.find_entries(
                    gateway, self.state.reader, self.state.transactions, file_path
                )
                if entries:
                    transaction, entry = entries[0]
                    summary.add_entry(
                        entry,
                        OpStatus.SUCCESS,
                        transaction.transaction_type,
                        None,
                        self._source_stat(entry.file_path),
                        compressed=entry.compressed,
                        input=util.path_to_str(file_path),
                    )
                else:
                    summary.add_file(util.path_to_str(file_path), OpStatus.SKIPPED)
            except UnknowFileTypeError:
                summary.add_file(
                    util.path_to_str(file_path), OpStatus.SKIPPED, "Not a known file type"
                )
            except FileNotExistsError:
                summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, "File not found")
            except PDBStoreException as exp:
                summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, "ex:" + str(exp))
            except Exception as exc:  # pylint: disable=broad-except # pragma: no cover
                summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, str(exc))
                output.error(f"unexpected error when querying information for {file_path}")
        return summary

    @staticmethod
    def _source_stat(file_path: PathLike) -> Optional[Any]:
        """Read the metadata of the file an entry was originally built from.

        The path recorded at add time may well have disappeared since, which is
        not an error worth failing the query for.
        """
        source = util.str_to_path(file_path)
        if source is None:
            return None
        try:
            return source.stat()
        except OSError:
            return None

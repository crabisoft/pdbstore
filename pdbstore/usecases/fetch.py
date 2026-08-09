"""Extract symbol files out of a symbol store."""

import os

from pdbstore import util
from pdbstore.entities.summary import OpStatus, Summary
from pdbstore.entities.transaction_type import TransactionType
from pdbstore.exceptions import FileNotExistsError, InvalidPEFile, PDBStoreException
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import List, Optional, PathLike
from pdbstore.usecases import lookup
from pdbstore.usecases.store_state import StoreState

__all__ = ["FetchSymbolsInteractor"]


class FetchSymbolsInteractor:
    """Retrieve the symbol file matching each input binary."""

    def __init__(self, state: StoreState):
        self.state = state

    def execute(self, files: List[PathLike], output_dir: Optional[PathLike] = None) -> Summary:
        """Fetch the symbol file of every input binary.

        :param files: The pe files whose symbols are wanted.
        :param output_dir: Optional directory receiving the symbol files.
            Defaults to the directory of each input file.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object.
        """
        output = PDBStoreOutput()
        gateway = self.state.gateway
        summary = Summary(None, OpStatus.SUCCESS, TransactionType.FETCH)

        output.verbose(f"Search pdb files for {len(files)} file(s)")

        for file_path in files:
            try:
                found = lookup.fetch_symbol(self.state.reader, self.state.transactions, file_path)
                if not found:
                    summary.add_file(file_path, OpStatus.SKIPPED, "Not found")
                    continue

                transaction, entry = found
                destination = output_dir or os.path.dirname(util.path_to_str(file_path))
                symbol_path = gateway.extract_entry(entry, destination)
                if symbol_path:
                    dct = summary.add_file(util.path_to_str(symbol_path), OpStatus.SUCCESS)
                    dct["input"] = util.path_to_str(file_path)
                else:
                    summary.add_file(
                        util.path_to_str(file_path),
                        OpStatus.FAILED,
                        f"Failed to extract from transaction {transaction.transaction_id}",
                    )
            except InvalidPEFile:
                summary.add_file(
                    util.path_to_str(file_path), OpStatus.SKIPPED, "Not a valid pe file"
                )
            except FileNotExistsError:
                summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, "File not found")
            except PDBStoreException as exp:  # pragma: no cover
                summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, "ex:" + str(exp))
            except Exception as exc:  # pylint: disable=broad-except # pragma: no cover
                summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, str(exc))
                output.error(exc)
                output.error(f"unexpected error when fetching information for {file_path}")
        return summary

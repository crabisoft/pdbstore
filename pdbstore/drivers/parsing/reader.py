"""Symbol file reader backed by the PE and PDB parsers."""

from pdbstore.io import file as fileinfo
from pdbstore.typing import Optional, PathLike, Tuple
from pdbstore.usecases.gateways.symbol_file import SymbolFileReader

__all__ = ["PdbSymbolFileReader"]


class PdbSymbolFileReader(SymbolFileReader):
    """Identify files by parsing their PE, PDB or portable PDB headers."""

    def signature_of(self, file_path: PathLike) -> Optional[str]:
        """Compute the signature a file is indexed under.

        :param file_path: Path to the file to be identified.
        :return: The signature if the file could be identified, else None.
        :raise:
            :FileNotExistsError: The specified file doesn't exist.
            :UnknowFileTypeError: The file is of an unsupported type.
        """
        # Resolved through the module rather than bound at import time, so that
        # the parsers stay substitutable in tests.
        return fileinfo.compute_hash_key(file_path)

    def debug_info_of(self, file_path: PathLike) -> Optional[Tuple[str, str]]:
        """Extract which symbol file a binary was built with.

        :param file_path: Path to the pe file to be inspected.
        :return: The symbol file name and its signature, or None when the
            binary carries no debugging information.
        :raise:
            :FileNotExistsError: The specified file doesn't exist.
            :InvalidPEFile: The file is not a valid pe file.
        """
        return fileinfo.extract_dbg_info(file_path)

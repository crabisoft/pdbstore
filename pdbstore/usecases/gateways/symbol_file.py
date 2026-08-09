"""Gateway reading the identity of a symbol or binary file.

Identifying a file means parsing a PE or PDB header, which is a file format
concern and therefore an outer layer one. The interactors only ever need the
answer — a signature, or the symbol file a binary was built with — so that is
all this gateway exposes.
"""

from abc import ABC, abstractmethod

from pdbstore.typing import Optional, PathLike, Tuple

__all__ = ["SymbolFileReader"]


class SymbolFileReader(ABC):
    """Extract the identity of symbol and binary files."""

    @abstractmethod
    def signature_of(self, file_path: PathLike) -> Optional[str]:
        """Compute the signature a file is indexed under.

        :param file_path: Path to the file to be identified.
        :return: The signature if the file could be identified, else None.
        :raise:
            :FileNotExistsError: The specified file doesn't exist.
            :UnknowFileTypeError: The file is of an unsupported type.
        """

    @abstractmethod
    def debug_info_of(self, file_path: PathLike) -> Optional[Tuple[str, str]]:
        """Extract which symbol file a binary was built with.

        :param file_path: Path to the pe file to be inspected.
        :return: The symbol file name and its signature, or None when the
            binary carries no debugging information.
        :raise:
            :FileNotExistsError: The specified file doesn't exist.
            :InvalidPEFile: The file is not a valid pe file.
        """

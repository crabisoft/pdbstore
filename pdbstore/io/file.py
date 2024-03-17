import ntpath
import os
import struct
import uuid
from pathlib import Path

import pefile as pe

from pdbstore import util
from pdbstore.exceptions import (
    FileNotExistsError,
    InvalidPEFile,
    ParseFileError,
    PDBSignatureNotFoundError,
    ReadFileError,
    UnknowFileTypeError,
)
from pdbstore.io import pdbfile as pdb
from pdbstore.io import portablepdbfile as portablepdb
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import Any, List, Optional, PathLike, Tuple, Union


def read_file(fname: PathLike, mode: str = "rb", encoding: Optional[str] = None) -> Any:
    """Read all contents of a file

    :return: The file contents
    :raise:
        :ReadFileError: An errors occurs when reading the file
    """
    content = None
    try:
        with open(fname, mode=mode, encoding=encoding) as fop:
            content = fop.read()
    except OSError as exc:
        raise ReadFileError(fname) from exc
    return content


def read_text_file(fname: PathLike, splitlines: Optional[bool] = False) -> Any:
    """Read all content of a text file

    :param fname: Path to the text file to be read
    :param splitlines: True to retrieve list of read lines, else False
                       to retrieve the text file content as it is
    :return: The file content
    :raise:
        :ReadFileError: An errors occurs when reading the file
    """
    if splitlines:
        try:
            with open(fname, mode="rt", encoding="utf-8") as fpt:
                return fpt.read().split("\n")
        except OSError as exc:
            raise ReadFileError(fname) from exc

    return read_file(fname, "rt", "utf-8")


def read_binary_file(fname: PathLike) -> Any:
    """Read all content of a binary file

    :param fname: Path to the text file to be read.
    :return: The file content.
    :raise:
        :ReadFileError: An errors occurs when reading the file.
    """
    return read_file(fname, "rb")


def compute_hash_key(file_path: PathLike) -> Union[str, None]:
    """Compute hash key given a file path

    :return: The computed hash key if successful, else None
    :raise:
        :FileNotExistsError: The specified file doesn't exists
        :UnknowFileTypeError: Unsupported file type
    """
    file_path = util.path_to_str(file_path)
    if not file_path or not os.path.exists(file_path):
        if file_path:
            raise FileNotExistsError(file_path)
        return None

    # Try to consider it as pe file
    try:
        # pylint: disable=no-member
        pefile = pe.PE(file_path, fast_load=True)
        return (
            f"{pefile.FILE_HEADER.TimeDateStamp:x}" f"{pefile.OPTIONAL_HEADER.SizeOfImage:x}"
        ).upper()
    except pe.PEFormatError:
        pass

    # Try to consider it as pdb file
    try:
        pdbfile = pdb.PDB(file_path)
        age_field = ""
        if pdbfile.age:
            age_field = f"{pdbfile.age:x}"
        return f"{pdbfile.guid}{age_field}".upper()
    except PDBSignatureNotFoundError:
        pass
    except ParseFileError:
        pass

    # Try to consider it as pdb file
    try:
        ppdbfile = portablepdb.PortablePDB(file_path)
        age_field = ""
        if ppdbfile.age:
            age_field = f"{ppdbfile.age:x}"
        return f"{ppdbfile.guid}{age_field}".upper()
    except PDBSignatureNotFoundError:
        pass
    except ParseFileError:
        pass

    # Unsupported file
    raise UnknowFileTypeError(file_path)


def extract_dbg_info(file_path: PathLike) -> Optional[Tuple[str, str]]:
    """Extract debugging information from  a pe file.

    :param file_path: Path to the pefile

    :return: A tuple containing debugging informations:

        * item[0]: The pdb file name
        * item[1]: The unique pdb file identifier

    :raise:
        :FileNotExistsError: The specified file doesn't exists
        :UnknowFileTypeError: Unsupported file type
        :InvalidPEFile: Invalid pe file (ex: exe or dll)
    """
    file_path = util.path_to_str(file_path)
    if not file_path or not os.path.exists(file_path):
        if file_path:
            raise FileNotExistsError(file_path)
        return None

    # Try to consider it as pe file
    try:
        # pylint: disable=no-member
        pefile = pe.PE(file_path, fast_load=True)
        pefile.parse_data_directories(
            directories=[pe.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DEBUG"]]
        )
        code_view_entry: Optional[pe.DebugData] = None
        for debug_entry in pefile.DIRECTORY_ENTRY_DEBUG:
            if pe.DEBUG_TYPE[debug_entry.struct.Type] == "IMAGE_DEBUG_TYPE_CODEVIEW":
                code_view_entry = debug_entry
                break

        if not code_view_entry:
            PDBStoreOutput().warning(
                f"{os.path.basename(file_path)} doesn't have symbol information"
            )
            return None

        symbol_type_offset = code_view_entry.struct.PointerToRawData
        symbol_type_size = code_view_entry.struct.SizeOfData
        symbol_type_data = pefile.__data__[
            symbol_type_offset : symbol_type_offset + symbol_type_size
        ]

        if symbol_type_data[:4] == b"RSDS":
            if code_view_entry.entry.PdbFileName[-1] == 0x0:
                pdb_filename = ntpath.basename(
                    code_view_entry.entry.PdbFileName[:-1].decode("utf-8")
                )
            else:
                pdb_filename = ntpath.basename(code_view_entry.entry.PdbFileName.decode("utf-8"))
            if hasattr(code_view_entry.entry, "Signature_Data5"):
                # recent pefile version
                fields = (
                    code_view_entry.entry.Signature_Data1,
                    code_view_entry.entry.Signature_Data2,
                    code_view_entry.entry.Signature_Data3,
                    code_view_entry.entry.Signature_Data4,
                    code_view_entry.entry.Signature_Data5,
                    code_view_entry.entry.Signature_Data6_value,
                )
            else:
                # pragma: no cover
                # old pefile version

                signature_data4 = code_view_entry.entry.Signature_Data4[0]
                signature_data5 = code_view_entry.entry.Signature_Data4[1]
                signature_data6 = struct.unpack(
                    ">Q",
                    b"\0\0" + code_view_entry.entry.Signature_Data4[2:],
                )[0]

                fields = (
                    code_view_entry.entry.Signature_Data1,
                    code_view_entry.entry.Signature_Data2,
                    code_view_entry.entry.Signature_Data3,
                    signature_data4,
                    signature_data5,
                    signature_data6,
                )
            guid = (
                str(uuid.UUID(fields=fields)).replace("-", "").upper()
                + f"{code_view_entry.entry.Age:X}"
            )
        else:
            PDBStoreOutput().error(f"{symbol_type_data[:4]} unsupported symbol type")
            raise InvalidPEFile(file_path)
        return pdb_filename, guid
    except pe.PEFormatError as pef:
        raise InvalidPEFile(file_path) from pef
    except BaseException:  # pylint: disable=broad-exception-caught
        pass
    return None


def build_files_list(
    files: Union[str, List[str]],
    recursive: bool = False,
    exist_only: bool = False,
) -> List[Path]:
    """Build list of required files given input file given by end-user

    This function analyzes ``files`` to build the list of required files, so:

        - recursive exploration if an entry is a directory
        - parse reponse file if an entry is formatted with ``@name`` logic
        - use the input file as it is if a file exists

    :param files: It can be a simple or a list of path
    :param recursive: True to explore recursively the specified directories, else False
    :param exist_only: True to retrieve the list of existing files, else False
    :return: List of Path object
    """
    if not files:
        return []

    def _explore_dirs(rootdir: str, recursive: bool = False) -> List[Path]:
        lst: List[Path] = []
        dirs: List[Path] = []
        for root, _, files in os.walk(rootdir):
            for lfile in files:
                fname = Path(os.path.join(root, lfile))
                if os.path.isdir(fname):
                    dirs.append(fname)
                else:
                    lst.append(fname)
            if not recursive:
                break

        for subdir in dirs:
            lst.extend(_explore_dirs(os.path.join(rootdir, subdir), False))
        return lst

    files_list: List[Path] = []
    for file_in in files if isinstance(files, list) else [files]:
        file = os.fspath(file_in)
        if file.startswith("@"):
            # parse response file
            fname = file[1:]
            if os.path.isfile(fname):
                curdir = os.getcwd()
                os.chdir(os.path.dirname(fname))
                with open(fname, "rt", encoding="utf-8") as fpr:
                    for line in fpr.readlines():
                        name = line.strip()
                        if os.path.isdir(name):
                            files_list.extend(_explore_dirs(name, False))
                        else:
                            files_list.append(Path(name))
                os.chdir(curdir)
        elif os.path.isdir(file):
            files_list.extend(_explore_dirs(file, recursive))
        elif not exist_only or os.path.exists(str(file)):
            files_list.append(Path(file))

    return files_list


def get_file_size(path: PathLike) -> int:
    """Get file size

    :param path: The file path
    :return: The file size
    """
    if not path:
        return 0
    file_path: Path = util.str_to_path(path)
    if not file_path or not file_path.exists():
        return 0

    return file_path.stat().st_size

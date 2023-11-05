import os
import re
from pathlib import Path

from pdbstore.typing import Any, Generator, List, Optional, PathLike, Union


def str_to_path(path: PathLike) -> Any:
    """Convert string or Path to Path

    :param path: The path to be converted
    :return: The converted path into Path object if successful, else None
    """
    if not path:
        return None

    if not isinstance(path, Path):
        try:
            new_path = Path(str(path))
        except RuntimeError:
            new_path = None
    else:
        new_path = path

    return new_path


def path_to_str(path: PathLike) -> Any:
    """Convert string or path to string only

    :param path: The path to be converted
    :return: The converted string from ``path`` if successful, else None
    """
    if not path:
        return None

    return os.fspath(path)


def abbreviate(input_path: PathLike, max_length: int = 40) -> PathLike:
    """Truncate a file path to fit with a given a maximum number of characters.

    :param file_path: The path to abbreviate.
    :param max_length: The maximum length to the truncated path.
    :return: The truncated path
    """
    file_path: str = str(input_path)
    first: bool = True
    ref: int = 0

    mparts: List[str] = list(
        filter(lambda e: e not in ["", "\\", "/"], re.split("(\\\\|/)", file_path))
    )
    file_name = mparts[-1]
    del mparts[-1]
    if re.match("^[a-zA-Z]:$", mparts[0]):
        mparts[0] += "\\"

    min_abb_len = 5 if mparts[0] == "/" else 6
    if max_length < (len(file_name) + min_abb_len):
        return file_name
    idx = int(len(mparts) / 2)
    mfile_path_s = file_path
    while len(mfile_path_s) > max_length:
        if (idx + ref) >= (idx * 2 + 1):
            break
        if first:
            mparts[idx + ref] = "..."
        else:
            mparts[idx + ref] = ""

        filtered = [] if file_path[0] != "/" else ["/"]
        for mpp in mparts:
            if mpp:
                filtered.append(mpp)
        filtered.append(file_name)
        mfile_path = Path(*tuple(filtered))
        mfile_path_s = os.fspath(mfile_path)
        if not first:
            ref *= -1
            if ref < 0:
                ref -= 1
        else:
            ref -= 1
            first = False

        if idx + ref >= max_length:
            ref -= 1

    if file_path.find("/") != -1:
        mfile_path_s = mfile_path_s.replace("\\", "/")
    elif file_path.find("\\") != -1:
        mfile_path_s = mfile_path_s.replace("\\/", "\\").replace("/", "\\")
    return mfile_path_s


def which(program: str, var_name: Optional[str] = None) -> Union[str, None]:
    """Retrieve the full path of a program given by its program name.
    This function will first check if the program exists as it is by testing
    the program name as it is. If not found, this function will try to find
    it using the PATH and PATHEXT environment variable.

    :param program: Specify the program name without file extension.
    :param var_name: Specify the name of the environment variable that can be use
                    to locate the requested program. This variable will be used
                    first before to search it using PATH environment variable.
    :return: The full path name of the requested program if found, else None
    to indicate that the program is not available.
    """

    def _is_exe(fpath: str) -> bool:
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    def _ext_candidates(fpath: str) -> Generator[str, None, None]:
        yield fpath
        for ext in os.environ.get("PATHEXT", "").split(os.pathsep):
            yield fpath + ext

    if var_name:
        for path in os.environ.get(var_name, "").split(os.pathsep):
            exe_file = os.path.join(path, program)
            for candidate in _ext_candidates(exe_file):
                if _is_exe(candidate):
                    return candidate

    fpath, _ = os.path.split(program)
    if fpath:
        if _is_exe(program):
            return program
    else:
        for path in os.environ.get("PATH", "").split(os.pathsep):
            exe_file = os.path.join(path, program)
            for candidate in _ext_candidates(exe_file):
                if _is_exe(candidate):
                    return candidate

    return None

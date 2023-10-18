import os
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
    :return: The truncate path
    """
    file_path: Path = str_to_path(input_path)
    cnt = 0
    ref = 0
    idx = int(len(file_path.parts) / 2)
    mparts: List[Optional[str]] = [
        *file_path.parts,
    ]
    mfile_path_s: str = os.fspath(file_path)
    while len(mfile_path_s) > max_length:
        if (idx + ref) <= 1:
            cnt += 1
        elif (idx + ref) >= (idx * 2 + 1):
            break
        if cnt == 0:
            mparts[idx + ref] = "..."
        else:
            mparts[idx + ref] = None

        filtered: List[str] = []
        for mpp in mparts:
            if mpp:
                filtered.append(mpp)
        mfile_path = Path(*tuple(filtered))
        mfile_path_s = os.fspath(mfile_path)
        if cnt != 0:
            ref *= -1
            if ref < 0:
                ref -= 1
        else:
            ref -= 1
        cnt += 1
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

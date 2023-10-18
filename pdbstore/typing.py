import argparse
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    IO,
    ItemsView,
    List,
    Mapping,
    Optional,
    overload,
    Sequence,
    Tuple,
    TYPE_CHECKING,
    TypedDict,
    TypeVar,
    Union,
)

__all__ = [
    "overload",
    "Any",
    "Callable",
    "Dict",
    "ExitCode",
    "Generator",
    "IO",
    "ItemsView",
    "List",
    "Optional",
    "Mapping",
    "PathLike",
    "Sequence",
    "SubParserType",
    "Tuple",
    "TYPE_CHECKING",
    "TypedDict",
    "TypeVar",
    "Union",
]


ExitCode = Union[str, int, None]
PathLike = Union[str, Path]

if TYPE_CHECKING:
    # pylint: disable=protected-access,line-too-long
    SubParserType = argparse._SubParsersAction["PDBStoreArgumentParser"]  # type: ignore[name-defined]
else:
    SubParserType = Any

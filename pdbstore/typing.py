import argparse
from pathlib import Path
from typing import (
    Any,
    BinaryIO,
    Callable,
    cast,
    Dict,
    Generator,
    IO,
    ItemsView,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    overload,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TYPE_CHECKING,
    TypedDict,
    TypeVar,
    Union,
)

__all__ = [
    "cast",
    "overload",
    "Any",
    "BinaryIO",
    "Callable",
    "Dict",
    "ExitCode",
    "Generator",
    "IO",
    "Iterable",
    "Iterator",
    "ItemsView",
    "List",
    "NamedTuple",
    "Optional",
    "Mapping",
    "PathLike",
    "Protocol",
    "Sequence",
    "Set",
    "StoreURI",
    "SubParserType",
    "Tuple",
    "TYPE_CHECKING",
    "TypedDict",
    "TypeVar",
    "Union",
]


ExitCode = Union[str, int, None]
PathLike = Union[str, Path]

StoreURI = str
"""Location of a symbol store.

It is either a local directory path or a scheme-qualified URI such as
``file:///var/symbols``. Additional schemes are registered by the blob store
factory (see :func:`pdbstore.drivers.blob.factory.create_blob_store`).
"""

if TYPE_CHECKING:
    # pylint: disable=protected-access,line-too-long
    SubParserType = argparse._SubParsersAction["PDBStoreArgumentParser"]  # type: ignore[name-defined]
else:
    SubParserType = Any

"""Resolution of a store location into a blob store.

A location is either a plain local directory or a scheme-qualified URI. Adding
a backend means registering one scheme here and implementing
:class:`BlobStore <pdbstore.usecases.gateways.blob_store.BlobStore>`; nothing
above this module has to change, and the resulting store keeps the very same
SymSrv layout.
"""

from urllib.parse import unquote, urlparse

from pdbstore import util
from pdbstore.drivers.blob.local import LocalBlobStore
from pdbstore.drivers.blob.memory import MemoryBlobStore
from pdbstore.exceptions import PDBStoreException
from pdbstore.typing import Callable, Dict, List, Optional, PathLike
from pdbstore.usecases.gateways.blob_store import BlobStore

__all__ = ["create_blob_store", "register_scheme", "supported_schemes"]

BlobStoreFactory = Callable[[str], BlobStore]

_FACTORIES: Dict[str, BlobStoreFactory] = {}


def register_scheme(scheme: str, factory: BlobStoreFactory) -> None:
    """Register the backend serving a URI scheme.

    :param scheme: The URI scheme, without the trailing ``://``.
    :param factory: A callable turning a location into a
        :class:`BlobStore <pdbstore.usecases.gateways.blob_store.BlobStore>`.
    """
    _FACTORIES[scheme.lower()] = factory


def supported_schemes() -> List[str]:
    """Retrieve the URI schemes a store location may use.

    :return: The registered schemes, in alphabetical order.
    """
    return sorted(_FACTORIES)


def create_blob_store(location: PathLike) -> BlobStore:
    """Build the blob store serving a location.

    :param location: A local directory path, or a URI such as
        ``file:///var/symbols``.
    :return: The :class:`BlobStore <pdbstore.usecases.gateways.blob_store.BlobStore>`
        serving ``location``.
    :raise:
        :PDBStoreException: The URI scheme has no registered backend.
    """
    text = util.path_to_str(location) or ""
    scheme = _scheme_of(text)
    if scheme is None:
        return LocalBlobStore(text)

    try:
        factory = _FACTORIES[scheme]
    except KeyError as exc:
        known = ", ".join(supported_schemes())
        raise PDBStoreException(
            f"{scheme}: unsupported symbol store scheme (expected one of: {known})"
        ) from exc
    return factory(text)


def _scheme_of(location: str) -> Optional[str]:
    """Extract the URI scheme of a location, if it has one.

    A single letter is never treated as a scheme, so a Windows path such as
    ``C:\\symbols`` stays a local directory.
    """
    parsed = urlparse(location)
    if len(parsed.scheme) < 2:
        return None
    return parsed.scheme.lower()


def _local_from_uri(location: str) -> BlobStore:
    """Build a local blob store out of a ``file://`` URI."""
    parsed = urlparse(location)
    path = unquote(parsed.path)
    if parsed.netloc:
        # A UNC location such as file://server/share
        path = f"//{parsed.netloc}{path}"
    return LocalBlobStore(path)


def _memory_from_uri(location: str) -> BlobStore:
    """Build an in-memory blob store out of a ``memory://`` URI."""
    return MemoryBlobStore(urlparse(location).netloc or "memory")


def _s3_from_uri(location: str) -> BlobStore:
    """Build an S3 blob store out of an ``s3://`` URI.

    Imported on demand so that boto3 stays optional: a store held on a local
    filesystem must not require it to be installed.
    """
    # pylint: disable=import-outside-toplevel
    from pdbstore.drivers.blob.s3 import S3BlobStore

    return S3BlobStore.from_uri(location)


register_scheme("file", _local_from_uri)
register_scheme("memory", _memory_from_uri)
register_scheme("s3", _s3_from_uri)

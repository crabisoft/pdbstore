"""Gateway giving access to raw bytes held at a key.

This gateway knows nothing about symbols, transactions or the SymSrv format:
it moves bytes to and from keys, and that is all. Everything above it — the
store layout, the transaction bookkeeping — is expressed once in
:class:`SymSrvGateway <pdbstore.adapters.symsrv.gateway.SymSrvGateway>`, so a
new backend only has to satisfy the small contract below to host a symbol
store that ``symsrv.dll`` and Visual Studio can read.

Only the storage administration interactors under
:mod:`pdbstore.usecases.storage` are allowed to depend on this gateway
directly: for them, keys *are* the subject matter. Every other interactor goes
through
:class:`SymbolStoreGateway <pdbstore.usecases.gateways.symbol_store.SymbolStoreGateway>`.

Implementations must be safe to use from several threads at once, since
entries of a single transaction are stored concurrently.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from pdbstore.typing import BinaryIO, Iterator, NamedTuple, Optional, PathLike

__all__ = ["BlobStat", "BlobStore"]


class BlobStat(NamedTuple):
    """Metadata describing a stored blob."""

    size: int
    """Size of the blob in bytes."""

    mtime: float
    """Modification time as a POSIX timestamp."""

    atime: float
    """Access time as a POSIX timestamp.

    Backends unable to track access times report the modification time
    instead, which makes the ``unused`` analysis degrade to "not modified
    since" rather than fail.
    """


class BlobStore(ABC):
    """Store and retrieve bytes held at a key.

    A key is a ``/``-separated, store-relative string as computed by
    :mod:`pdbstore.entities.symsrv_layout`. It is up to the implementation to
    translate it into a path, an object name or anything else.
    """

    @property
    @abstractmethod
    def location(self) -> str:
        """Describe where this store keeps its data.

        Used for logging and reporting only, never to compute a key.

        :return: A human readable location, such as a directory or a URI.
        """

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Determine whether anything is stored under a key.

        Implementations must answer without transferring the blob content, so
        that a read-through composition stays affordable.

        :param key: The key to be checked.
        :return: True when something is stored under ``key``, else False.
        """

    @abstractmethod
    def is_blob(self, key: str) -> bool:
        """Determine whether a key holds readable content.

        Distinct from :meth:`exists` because a filesystem backend may resolve a
        key onto a directory, which exists but holds no content of its own.
        Backends without containers implement both identically.

        :param key: The key to be checked.
        :return: True when ``key`` holds content, else False.
        """

    @abstractmethod
    def stat(self, key: str) -> Optional[BlobStat]:
        """Retrieve the metadata of a blob.

        :param key: The key to be inspected.
        :return: The :class:`BlobStat` if the blob exists, else None.
        """

    @abstractmethod
    def list(self, prefix: str = "") -> Iterator[str]:
        """Iterate over the keys starting with a prefix.

        :param prefix: The key prefix to be listed. An empty prefix lists the
            whole store.
        :return: An iterator over the matching keys.
        """

    @abstractmethod
    def read_bytes(self, key: str) -> bytes:
        """Read the whole content of a blob.

        :param key: The key to be read.
        :return: The blob content.
        :raise:
            :ReadFileError: The blob cannot be read.
        """

    @abstractmethod
    def read_tail(self, key: str, size: int) -> bytes:
        """Read the last bytes of a blob.

        Kept in the contract rather than expressed as a full read because the
        history file is appended to on every operation and only its last
        character matters. Object stores serve this with a suffix range
        request, so the cost stays independent of the blob size.

        :param key: The key to be read.
        :param size: The number of trailing bytes to read.
        :return: The trailing bytes, shorter than ``size`` when the blob is
            smaller, empty when the blob is missing.
        """

    @abstractmethod
    def write_bytes(self, key: str, data: bytes) -> None:
        """Write the whole content of a blob, replacing it when it exists.

        :param key: The key to be written.
        :param data: The content to be stored.
        :raise:
            :WriteFileError: The blob cannot be written.
        """

    @abstractmethod
    def append_bytes(self, key: str, data: bytes) -> None:
        """Append data at the end of a blob, creating it when missing.

        Object stores have no native append, so implementations backed by one
        have to read, concatenate and write back. They are responsible for
        making that sequence safe against concurrent writers.

        :param key: The key to be extended.
        :param data: The content to be appended.
        :raise:
            :WriteFileError: The blob cannot be written.
        """

    @abstractmethod
    def open_stream(self, key: str) -> BinaryIO:
        """Open a blob for streamed reading.

        :param key: The key to be read.
        :return: A binary stream positioned at the beginning of the blob.
        :raise:
            :ReadFileError: The blob cannot be read.
        """

    @abstractmethod
    def write_stream(self, key: str, stream: BinaryIO) -> None:
        """Write a blob from a stream, replacing it when it exists.

        :param key: The key to be written.
        :param stream: The binary stream to be consumed.
        :raise:
            :WriteFileError: The blob cannot be written.
        """

    @abstractmethod
    def put_file(self, local_path: PathLike, key: str) -> None:
        """Store a local file under a key.

        Preferred over :meth:`write_bytes` for symbol files, which are large
        enough that holding them in memory is not an option.

        :param local_path: Path to the local file to be stored.
        :param key: The destination key.
        :raise:
            :CopyFileError: The file cannot be stored.
        """

    @abstractmethod
    def get_file(self, key: str, local_path: PathLike) -> None:
        """Retrieve a blob into a local file.

        :param key: The key to be retrieved.
        :param local_path: Path to the local file to be written.
        :raise:
            :CopyFileError: The blob cannot be retrieved.
        """

    @abstractmethod
    def copy(self, src_key: str, dst_key: str) -> None:
        """Duplicate a blob inside this store.

        :param src_key: The key to be copied.
        :param dst_key: The destination key.
        :raise:
            :CopyFileError: The blob cannot be copied.
        """

    @abstractmethod
    def move(self, src_key: str, dst_key: str) -> None:
        """Rename a blob inside this store.

        :param src_key: The key to be moved.
        :param dst_key: The destination key.
        :raise:
            :RenameFileError: The blob cannot be moved.
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove a blob, doing nothing when it is already absent.

        :param key: The key to be removed.
        """

    @abstractmethod
    def delete_prefix(self, prefix: str) -> None:
        """Remove every blob whose key starts with a prefix.

        :param prefix: The key prefix to be removed.
        """

    @abstractmethod
    def make_container(self, prefix: str) -> None:
        """Prepare a store to receive blobs under a prefix.

        Filesystem backends create the intermediate directories. Object stores
        have no such notion and treat this as a no-op.

        :param prefix: The key prefix to be prepared.
        """

    def local_path(self, key: str) -> Optional[Path]:
        """Retrieve the local path of a blob when it happens to have one.

        Returns None for any backend that does not keep its blobs on a
        filesystem. Callers must always provide a fallback based on
        :meth:`get_file`; this is strictly an optimisation used to hand a real
        path to an external tool such as the cab compressor.

        :param key: The key to be located.
        :return: The local path if this store is filesystem backed, else None.
        """
        # pylint: disable=unused-argument
        return None

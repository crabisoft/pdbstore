"""Blob store keeping everything in memory."""

import io
import time

from pdbstore import exceptions
from pdbstore.entities import symsrv_layout
from pdbstore.typing import BinaryIO, Dict, Iterator, Optional, PathLike, Tuple
from pdbstore.usecases.gateways.blob_store import BlobStat, BlobStore

__all__ = ["MemoryBlobStore"]


class MemoryBlobStore(BlobStore):
    """Keep the blobs of a symbol store in a dictionary.

    Useful to exercise the interactors without touching a disk, and to run the
    blob store contract suite against a backend that has no containers at all —
    which is what an object store looks like.
    """

    def __init__(self, name: str = "memory") -> None:
        self._name = name
        self._blobs: Dict[str, bytes] = {}
        self._times: Dict[str, Tuple[float, float]] = {}

    @property
    def location(self) -> str:
        """Describe where this store keeps its data.

        :return: A pseudo URI naming this in-memory store.
        """
        return f"memory://{self._name}"

    def exists(self, key: str) -> bool:
        """Determine whether anything is stored under a key.

        :param key: The key to be checked.
        :return: True when a blob is stored at or below ``key``, else False.
        """
        if key in self._blobs:
            return True
        container = key + symsrv_layout.KEY_SEPARATOR
        return any(stored.startswith(container) for stored in self._blobs)

    def is_blob(self, key: str) -> bool:
        """Determine whether a key holds readable content.

        :param key: The key to be checked.
        :return: True when a blob is stored under ``key``, else False.
        """
        return key in self._blobs

    def stat(self, key: str) -> Optional[BlobStat]:
        """Retrieve the metadata of a blob.

        :param key: The key to be inspected.
        :return: The metadata if the blob exists, else None.
        """
        if key not in self._blobs:
            return None
        mtime, atime = self._times[key]
        return BlobStat(size=len(self._blobs[key]), mtime=mtime, atime=atime)

    def list(self, prefix: str = "") -> Iterator[str]:
        """Iterate over the keys starting with a prefix.

        :param prefix: The key prefix to be listed.
        :return: An iterator over the matching keys, in key order.
        """
        container = prefix + symsrv_layout.KEY_SEPARATOR if prefix else ""
        for key in sorted(self._blobs):
            if not prefix or key == prefix or key.startswith(container):
                yield key

    def read_bytes(self, key: str) -> bytes:
        """Read the whole content of a blob.

        :param key: The key to be read.
        :return: The blob content.
        :raise:
            :ReadFileError: No blob is stored under ``key``.
        """
        try:
            content = self._blobs[key]
        except KeyError as exc:
            raise exceptions.ReadFileError(key) from exc
        self._touch(key, access_only=True)
        return content

    def read_tail(self, key: str, size: int) -> bytes:
        """Read the last bytes of a blob.

        :param key: The key to be read.
        :param size: The number of trailing bytes to read.
        :return: The trailing bytes, empty when the blob is missing.
        """
        content = self._blobs.get(key)
        if content is None:
            return b""
        return content[-size:] if size else b""

    def write_bytes(self, key: str, data: bytes) -> None:
        """Write the whole content of a blob.

        :param key: The key to be written.
        :param data: The content to be stored.
        """
        self._blobs[key] = bytes(data)
        self._touch(key)

    def append_bytes(self, key: str, data: bytes) -> None:
        """Append data at the end of a blob.

        :param key: The key to be extended.
        :param data: The content to be appended.
        """
        self._blobs[key] = self._blobs.get(key, b"") + bytes(data)
        self._touch(key)

    def open_stream(self, key: str) -> BinaryIO:
        """Open a blob for streamed reading.

        :param key: The key to be read.
        :return: A binary stream over the blob content.
        :raise:
            :ReadFileError: No blob is stored under ``key``.
        """
        return io.BytesIO(self.read_bytes(key))

    def write_stream(self, key: str, stream: BinaryIO) -> None:
        """Write a blob from a stream.

        :param key: The key to be written.
        :param stream: The binary stream to be consumed.
        """
        self.write_bytes(key, stream.read())

    def put_file(self, local_path: PathLike, key: str) -> None:
        """Store a local file under a key.

        :param local_path: Path to the local file to be stored.
        :param key: The destination key.
        :raise:
            :CopyFileError: The file cannot be read.
        """
        try:
            with open(local_path, "rb") as stream:
                self.write_bytes(key, stream.read())
        except OSError as exc:
            raise exceptions.CopyFileError(local_path, key) from exc

    def get_file(self, key: str, local_path: PathLike) -> None:
        """Retrieve a blob into a local file.

        :param key: The key to be retrieved.
        :param local_path: Path to the local file to be written.
        :raise:
            :CopyFileError: The blob cannot be written out.
        """
        try:
            content = self.read_bytes(key)
            with open(local_path, "wb") as stream:
                stream.write(content)
        except OSError as exc:
            raise exceptions.CopyFileError(key, local_path) from exc

    def copy(self, src_key: str, dst_key: str) -> None:
        """Duplicate a blob inside this store.

        :param src_key: The key to be copied.
        :param dst_key: The destination key.
        :raise:
            :CopyFileError: No blob is stored under ``src_key``.
        """
        if src_key not in self._blobs:
            raise exceptions.CopyFileError(src_key, dst_key)
        self.write_bytes(dst_key, self._blobs[src_key])

    def move(self, src_key: str, dst_key: str) -> None:
        """Rename a blob inside this store.

        :param src_key: The key to be moved.
        :param dst_key: The destination key.
        :raise:
            :RenameFileError: No blob is stored under ``src_key``.
        """
        if src_key not in self._blobs:
            raise exceptions.RenameFileError(src_key, dst_key)
        self.write_bytes(dst_key, self._blobs[src_key])
        self.delete(src_key)

    def delete(self, key: str) -> None:
        """Remove a blob.

        :param key: The key to be removed.
        """
        self._blobs.pop(key, None)
        self._times.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        """Remove every blob whose key starts with a prefix.

        :param prefix: The key prefix to be removed.
        """
        for key in list(self.list(prefix)):
            self.delete(key)

    def make_container(self, prefix: str) -> None:
        """Prepare a store to receive blobs under a prefix.

        An in-memory store has no container, so nothing has to be created.

        :param prefix: The key prefix to be prepared.
        """

    def _touch(self, key: str, access_only: bool = False) -> None:
        """Refresh the timestamps attached to a key."""
        now = time.time()
        mtime = self._times.get(key, (now, now))[0] if access_only else now
        self._times[key] = (mtime, now)

    def __len__(self) -> int:
        """Retrieve the total number of stored blobs."""
        return len(self._blobs)

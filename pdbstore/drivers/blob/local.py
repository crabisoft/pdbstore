"""Blob store backed by a local filesystem."""

import os
import shutil
from pathlib import Path

from pdbstore import exceptions, util
from pdbstore.entities import symsrv_layout
from pdbstore.typing import BinaryIO, Iterator, Optional, PathLike
from pdbstore.usecases.gateways.blob_store import BlobStat, BlobStore

__all__ = ["LocalBlobStore"]


class LocalBlobStore(BlobStore):
    """Keep the blobs of a symbol store in a local directory tree.

    A key maps directly onto a path below the root directory, so the resulting
    layout is byte for byte the one ``symstore.exe`` produces and the one
    ``symsrv.dll`` expects.
    """

    def __init__(self, rootdir: PathLike):
        self.rootdir: Path = util.str_to_path(rootdir)

    @property
    def location(self) -> str:
        """Describe where this store keeps its data.

        :return: The root directory as a string.
        """
        return str(self.rootdir)

    def path_of(self, key: str) -> Path:
        """Translate a store key into a local path.

        :param key: The key to be translated.
        :return: The corresponding local path.
        """
        parts = symsrv_layout.split_key(key)
        if not parts:
            return self.rootdir
        return self.rootdir.joinpath(*parts)

    def local_path(self, key: str) -> Optional[Path]:
        """Retrieve the local path of a blob.

        :param key: The key to be located.
        :return: The corresponding local path.
        """
        return self.path_of(key)

    def exists(self, key: str) -> bool:
        """Determine whether anything is stored under a key.

        :param key: The key to be checked.
        :return: True when the path exists, else False.
        """
        return self.path_of(key).exists()

    def is_blob(self, key: str) -> bool:
        """Determine whether a key holds readable content.

        :param key: The key to be checked.
        :return: True when the path is a regular file, else False.
        """
        return self.path_of(key).is_file()

    def stat(self, key: str) -> Optional[BlobStat]:
        """Retrieve the metadata of a blob.

        :param key: The key to be inspected.
        :return: The metadata if the file exists, else None.
        """
        path = self.path_of(key)
        try:
            info: os.stat_result = path.stat()
        except OSError:
            return None
        return BlobStat(size=info.st_size, mtime=info.st_mtime, atime=info.st_atime)

    def list(self, prefix: str = "") -> Iterator[str]:
        """Iterate over the keys starting with a prefix.

        :param prefix: The key prefix to be listed.
        :return: An iterator over the matching keys.
        """
        root = self.path_of(prefix)
        if root.is_file():
            yield prefix
            return
        if not root.is_dir():
            return
        for current, _, files in os.walk(os.fspath(root)):
            rel = os.path.relpath(current, os.fspath(self.rootdir))
            parts = [] if rel == "." else rel.split(os.sep)
            for name in sorted(files):
                yield symsrv_layout.join_key(*parts, name)

    def read_bytes(self, key: str) -> bytes:
        """Read the whole content of a blob.

        :param key: The key to be read.
        :return: The file content.
        :raise:
            :ReadFileError: The file cannot be read.
        """
        path = self.path_of(key)
        try:
            with open(path, "rb") as stream:
                content: bytes = stream.read()
        except OSError as exc:
            raise exceptions.ReadFileError(path) from exc
        return content

    def read_tail(self, key: str, size: int) -> bytes:
        """Read the last bytes of a blob.

        :param key: The key to be read.
        :param size: The number of trailing bytes to read.
        :return: The trailing bytes, empty when the file is missing.
        """
        path = self.path_of(key)
        try:
            with open(path, "rb") as stream:
                stream.seek(0, os.SEEK_END)
                offset = min(size, stream.tell())
                stream.seek(-offset, os.SEEK_END)
                content: bytes = stream.read(offset)
        except OSError:
            return b""
        return content

    def write_bytes(self, key: str, data: bytes) -> None:
        """Write the whole content of a blob.

        :param key: The key to be written.
        :param data: The content to be stored.
        :raise:
            :WriteFileError: The file cannot be written.
        """
        path = self.path_of(key)
        try:
            self._make_parent(path)
            with open(path, "wb") as stream:
                stream.write(data)
        except OSError as exc:
            raise exceptions.WriteFileError(path) from exc

    def append_bytes(self, key: str, data: bytes) -> None:
        """Append data at the end of a blob.

        :param key: The key to be extended.
        :param data: The content to be appended.
        :raise:
            :WriteFileError: The file cannot be written.
        """
        path = self.path_of(key)
        try:
            self._make_parent(path)
            with open(path, "ab") as stream:
                stream.write(data)
        except OSError as exc:
            raise exceptions.WriteFileError(path) from exc

    def open_stream(self, key: str) -> BinaryIO:
        """Open a blob for streamed reading.

        :param key: The key to be read.
        :return: A binary stream positioned at the beginning of the file.
        :raise:
            :ReadFileError: The file cannot be read.
        """
        path = self.path_of(key)
        try:
            # The caller owns the returned stream and is expected to close it.
            return open(path, "rb")  # pylint: disable=consider-using-with
        except OSError as exc:
            raise exceptions.ReadFileError(path) from exc

    def write_stream(self, key: str, stream: BinaryIO) -> None:
        """Write a blob from a stream.

        :param key: The key to be written.
        :param stream: The binary stream to be consumed.
        :raise:
            :WriteFileError: The file cannot be written.
        """
        path = self.path_of(key)
        try:
            self._make_parent(path)
            with open(path, "wb") as target:
                shutil.copyfileobj(stream, target)
        except OSError as exc:
            raise exceptions.WriteFileError(path) from exc

    def put_file(self, local_path: PathLike, key: str) -> None:
        """Store a local file under a key.

        :param local_path: Path to the local file to be stored.
        :param key: The destination key.
        :raise:
            :CopyFileError: The file cannot be stored.
        """
        path = self.path_of(key)
        try:
            self._make_parent(path)
            shutil.copy(local_path, path)
        except Exception as exc:
            raise exceptions.CopyFileError(local_path, path) from exc

    def get_file(self, key: str, local_path: PathLike) -> None:
        """Retrieve a blob into a local file.

        :param key: The key to be retrieved.
        :param local_path: Path to the local file to be written.
        :raise:
            :CopyFileError: The file cannot be retrieved.
        """
        path = self.path_of(key)
        try:
            shutil.copy(path, local_path)
        except Exception as exc:
            raise exceptions.CopyFileError(path, local_path) from exc

    def copy(self, src_key: str, dst_key: str) -> None:
        """Duplicate a blob inside this store.

        :param src_key: The key to be copied.
        :param dst_key: The destination key.
        :raise:
            :CopyFileError: The file cannot be copied.
        """
        src = self.path_of(src_key)
        dst = self.path_of(dst_key)
        try:
            self._make_parent(dst)
            shutil.copyfile(src, dst)
        except Exception as exc:
            raise exceptions.CopyFileError(src, dst) from exc

    def move(self, src_key: str, dst_key: str) -> None:
        """Rename a blob inside this store.

        :param src_key: The key to be moved.
        :param dst_key: The destination key.
        :raise:
            :RenameFileError: The file cannot be moved.
        """
        src = self.path_of(src_key)
        dst = self.path_of(dst_key)
        try:
            self._make_parent(dst)
            os.rename(src, dst)
        except OSError as exc:
            raise exceptions.RenameFileError(src, dst) from exc

    def delete(self, key: str) -> None:
        """Remove a blob.

        :param key: The key to be removed.
        """
        path = self.path_of(key)
        try:
            path.unlink()
        except OSError:
            pass

    def delete_prefix(self, prefix: str) -> None:
        """Remove every blob whose key starts with a prefix.

        Empty parent directories are pruned as well, so that deleting the last
        signature of a symbol also removes the directory named after it and the
        tree keeps the shape ``symstore.exe`` would have produced.

        :param prefix: The key prefix to be removed.
        """
        path = self.path_of(prefix)
        if path.is_file():
            self.delete(prefix)
        elif path.is_dir():
            shutil.rmtree(os.fspath(path))
        else:
            return

        parent = path.parent
        while parent != self.rootdir and parent.is_dir():
            try:
                if os.listdir(os.fspath(parent)):
                    break
                shutil.rmtree(os.fspath(parent))
            except OSError:
                break
            parent = parent.parent

    def make_container(self, prefix: str) -> None:
        """Create the directory holding the blobs under a prefix.

        :param prefix: The key prefix to be prepared.
        """
        path = self.path_of(prefix)
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _make_parent(path: Path) -> None:
        """Create the parent directory of a path when missing."""
        parent = path.parent
        if not parent.is_dir():
            parent.mkdir(parents=True, exist_ok=True)

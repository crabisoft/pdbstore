"""Blob store backed by Amazon S3, or any S3-compatible object store.

The layout written here is the very same one the local backend produces, so a
store held in a bucket stays a valid SymSrv store. Two properties of object
storage nevertheless have to be worked around, and both are handled below
rather than pushed onto the caller:

*Appending.* Object stores have no append. ``server.txt`` and ``history.txt``
are extended on every operation, so each append becomes a read, a concatenation
and a write. Left naive, two builds publishing at the same moment would each
write over the other and one transaction would silently vanish. Every such
write is therefore made conditional on the object not having changed in the
meantime, and retried when it has — see :meth:`S3BlobStore.append_bytes`.

*Access times.* S3 reports when an object was last written, never when it was
last read. :attr:`BlobStat.atime` therefore carries the modification time, and
the ``unused`` analysis degrades from "nobody debugged this since" to "nobody
published this since". For a symbol store, whose objects are written once and
never modified, that amounts to the age of the symbol.
"""

import os
from urllib.parse import urlparse

from pdbstore import exceptions
from pdbstore.entities import symsrv_layout
from pdbstore.typing import Any, BinaryIO, Dict, Iterator, List, Optional, PathLike
from pdbstore.usecases.gateways.blob_store import BlobStat, BlobStore

__all__ = ["S3BlobStore"]

_MISSING_CODES = frozenset({"404", "NoSuchKey", "NotFound"})
"""What S3 answers when an object is simply not there."""

_PRECONDITION_CODES = frozenset({"PreconditionFailed", "412", "ConditionalRequestConflict"})
"""What S3 answers when someone else wrote first."""

_DELETE_BATCH = 1000
"""Largest number of keys ``DeleteObjects`` accepts in one call."""


class S3BlobStore(BlobStore):
    """Keep the blobs of a symbol store as objects in a bucket."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        client: Optional[Any] = None,
        conditional_writes: bool = True,
        max_attempts: int = 8,
    ):
        """Build a store over a bucket.

        :param bucket: The bucket holding the store.
        :param prefix: Optional key prefix, so that one bucket can host several
            stores.
        :param client: Optional pre-built boto3 S3 client. Built from the
            environment when omitted.
        :param conditional_writes: True to guard concurrent appends. Turning
            this off risks losing a transaction when two writers publish at the
            same time, and is only there for object stores that reject
            conditional requests.
        :param max_attempts: How many times an append retries before giving up.
        """
        self.bucket = bucket
        self.prefix = prefix.strip(symsrv_layout.KEY_SEPARATOR)
        self.conditional_writes = conditional_writes
        self.max_attempts = max_attempts
        self._client = client if client is not None else _build_client()

    @classmethod
    def from_uri(cls, location: str, **kwargs: Any) -> "S3BlobStore":
        """Build a store out of an ``s3://bucket/prefix`` URI.

        :param location: The URI naming the bucket and optional prefix.
        :param kwargs: Extra arguments forwarded to the constructor.
        :return: The :class:`S3BlobStore` serving ``location``.
        :raise:
            :PDBStoreException: The URI names no bucket.
        """
        parsed = urlparse(location)
        if not parsed.netloc:
            raise exceptions.PDBStoreException(
                f"{location}: no bucket given (expected s3://bucket/optional/prefix)"
            )
        return cls(parsed.netloc, parsed.path, **kwargs)

    @property
    def location(self) -> str:
        """Describe where this store keeps its data.

        :return: The ``s3://bucket/prefix`` URI of the store.
        """
        if self.prefix:
            return f"s3://{self.bucket}/{self.prefix}"
        return f"s3://{self.bucket}"

    #
    # Key mapping
    #

    def object_key(self, key: str) -> str:
        """Translate a store key into an object key.

        :param key: The store key to be translated.
        :return: The key of the corresponding object.
        """
        return symsrv_layout.join_key(self.prefix, key)

    def store_key(self, object_key: str) -> str:
        """Translate an object key back into a store key.

        :param object_key: The object key to be translated.
        :return: The corresponding store key.
        """
        if not self.prefix:
            return object_key
        head = self.prefix + symsrv_layout.KEY_SEPARATOR
        return object_key[len(head) :] if object_key.startswith(head) else object_key

    #
    # Reading
    #

    def exists(self, key: str) -> bool:
        """Determine whether anything is stored under a key.

        :param key: The key to be checked.
        :return: True when an object is stored at or below ``key``, else False.
        """
        if self.is_blob(key):
            return True
        # A key may name no object of its own and still hold others below it,
        # which is what a directory looks like on a filesystem backend.
        response = self._client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=self.object_key(key) + symsrv_layout.KEY_SEPARATOR,
            MaxKeys=1,
        )
        found: int = response.get("KeyCount", 0)
        return found > 0

    def is_blob(self, key: str) -> bool:
        """Determine whether a key holds readable content.

        :param key: The key to be checked.
        :return: True when an object is stored under ``key``, else False.
        """
        return self._head(key) is not None

    def stat(self, key: str) -> Optional[BlobStat]:
        """Retrieve the metadata of a blob.

        S3 does not track when an object was last read, so the access time
        reported here is the modification time.

        :param key: The key to be inspected.
        :return: The metadata if the object exists, else None.
        """
        head = self._head(key)
        if head is None:
            return None
        modified = head["LastModified"].timestamp()
        return BlobStat(size=head["ContentLength"], mtime=modified, atime=modified)

    def list(self, prefix: str = "") -> Iterator[str]:
        """Iterate over the keys starting with a prefix.

        :param prefix: The key prefix to be listed.
        :return: An iterator over the matching keys, in key order.
        """
        if prefix and self.is_blob(prefix):
            yield prefix
            return

        search = self.object_key(prefix)
        if search:
            search += symsrv_layout.KEY_SEPARATOR
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=search):
            for item in page.get("Contents", []):
                yield self.store_key(item["Key"])

    def read_bytes(self, key: str) -> bytes:
        """Read the whole content of a blob.

        :param key: The key to be read.
        :return: The object content.
        :raise:
            :ReadFileError: The object cannot be read.
        """
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=self.object_key(key))
            content: bytes = response["Body"].read()
        except Exception as exc:
            raise exceptions.ReadFileError(self._describe(key)) from exc
        return content

    def read_tail(self, key: str, size: int) -> bytes:
        """Read the last bytes of a blob.

        Served by a suffix range request, so the cost does not grow with the
        size of the object.

        :param key: The key to be read.
        :param size: The number of trailing bytes to read.
        :return: The trailing bytes, empty when the object is missing or empty.
        """
        if size <= 0:
            return b""
        try:
            response = self._client.get_object(
                Bucket=self.bucket, Key=self.object_key(key), Range=f"bytes=-{size}"
            )
            content: bytes = response["Body"].read()
        except Exception:  # pylint: disable=broad-exception-caught
            # Either the object is missing, or it is empty and no range can
            # address it. Both mean there is no tail to report.
            return b""
        return content

    def open_stream(self, key: str) -> BinaryIO:
        """Open a blob for streamed reading.

        :param key: The key to be read.
        :return: A binary stream over the object content.
        :raise:
            :ReadFileError: The object cannot be read.
        """
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=self.object_key(key))
        except Exception as exc:
            raise exceptions.ReadFileError(self._describe(key)) from exc
        stream: BinaryIO = response["Body"]
        return stream

    def get_file(self, key: str, local_path: PathLike) -> None:
        """Retrieve a blob into a local file.

        :param key: The key to be retrieved.
        :param local_path: Path to the local file to be written.
        :raise:
            :CopyFileError: The object cannot be retrieved.
        """
        target = os.fspath(local_path)
        try:
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._client.download_file(self.bucket, self.object_key(key), target)
        except Exception as exc:
            raise exceptions.CopyFileError(self._describe(key), local_path) from exc

    #
    # Writing
    #

    def write_bytes(self, key: str, data: bytes) -> None:
        """Write the whole content of a blob.

        :param key: The key to be written.
        :param data: The content to be stored.
        :raise:
            :WriteFileError: The object cannot be written.
        """
        try:
            self._client.put_object(Bucket=self.bucket, Key=self.object_key(key), Body=data)
        except Exception as exc:
            raise exceptions.WriteFileError(self._describe(key)) from exc

    def append_bytes(self, key: str, data: bytes) -> None:
        """Append data at the end of a blob, creating it when missing.

        There is no append in an object store, so the object is read, extended
        and written back. That sequence is only safe if nothing else wrote in
        between, which is what the condition on each write checks: creation is
        conditional on the object being absent, extension on it still carrying
        the ETag that was just read. A writer that loses the race simply reads
        the winner's version and tries again, so no append is ever lost.

        :param key: The key to be extended.
        :param data: The content to be appended.
        :raise:
            :WriteFileError: The object cannot be written, or too many writers
                are contending for it.
        """
        if not self.conditional_writes:
            self.write_bytes(key, self._current(key) + data)
            return

        object_key = self.object_key(key)
        for _ in range(self.max_attempts):
            head = self._head(key)
            try:
                if head is None:
                    self._client.put_object(
                        Bucket=self.bucket, Key=object_key, Body=data, IfNoneMatch="*"
                    )
                else:
                    self._client.put_object(
                        Bucket=self.bucket,
                        Key=object_key,
                        Body=self.read_bytes(key) + data,
                        IfMatch=head["ETag"],
                    )
                return
            except Exception as exc:  # pylint: disable=broad-exception-caught
                if not _is_precondition_failure(exc):
                    raise exceptions.WriteFileError(self._describe(key)) from exc
                # Somebody else got there first; read their version and retry.

        raise exceptions.WriteFileError(
            self._describe(key),
            f"failed to append after {self.max_attempts} attempts: too many concurrent writers",
        )

    def write_stream(self, key: str, stream: BinaryIO) -> None:
        """Write a blob from a stream.

        :param key: The key to be written.
        :param stream: The binary stream to be consumed.
        :raise:
            :WriteFileError: The object cannot be written.
        """
        try:
            self._client.upload_fileobj(stream, self.bucket, self.object_key(key))
        except Exception as exc:
            raise exceptions.WriteFileError(self._describe(key)) from exc

    def put_file(self, local_path: PathLike, key: str) -> None:
        """Store a local file under a key.

        :param local_path: Path to the local file to be stored.
        :param key: The destination key.
        :raise:
            :CopyFileError: The file cannot be stored.
        """
        try:
            self._client.upload_file(os.fspath(local_path), self.bucket, self.object_key(key))
        except Exception as exc:
            raise exceptions.CopyFileError(local_path, self._describe(key)) from exc

    #
    # Structure
    #

    def copy(self, src_key: str, dst_key: str) -> None:
        """Duplicate a blob inside this store.

        :param src_key: The key to be copied.
        :param dst_key: The destination key.
        :raise:
            :CopyFileError: The object cannot be copied.
        """
        try:
            self._client.copy_object(
                Bucket=self.bucket,
                Key=self.object_key(dst_key),
                CopySource={"Bucket": self.bucket, "Key": self.object_key(src_key)},
            )
        except Exception as exc:
            raise exceptions.CopyFileError(
                self._describe(src_key), self._describe(dst_key)
            ) from exc

    def move(self, src_key: str, dst_key: str) -> None:
        """Rename a blob inside this store.

        S3 has no rename, so the object is copied and the original removed.

        :param src_key: The key to be moved.
        :param dst_key: The destination key.
        :raise:
            :RenameFileError: The object cannot be moved.
        """
        try:
            self.copy(src_key, dst_key)
        except exceptions.CopyFileError as exc:
            raise exceptions.RenameFileError(
                self._describe(src_key), self._describe(dst_key)
            ) from exc
        self.delete(src_key)

    def delete(self, key: str) -> None:
        """Remove a blob.

        :param key: The key to be removed.
        """
        try:
            self._client.delete_object(Bucket=self.bucket, Key=self.object_key(key))
        except Exception:  # pylint: disable=broad-except # pragma: no cover
            pass

    def delete_prefix(self, prefix: str) -> None:
        """Remove every blob whose key starts with a prefix.

        :param prefix: The key prefix to be removed.
        """
        batch: List[Dict[str, str]] = []
        for key in list(self.list(prefix)):
            batch.append({"Key": self.object_key(key)})
            if len(batch) == _DELETE_BATCH:
                self._delete_batch(batch)
                batch = []
        if batch:
            self._delete_batch(batch)

    def make_container(self, prefix: str) -> None:
        """Prepare a store to receive blobs under a prefix.

        An object store has no containers, so nothing has to be created.

        :param prefix: The key prefix to be prepared.
        """

    #
    # Internals
    #

    def _head(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch the metadata of an object, or None when it does not exist."""
        try:
            head: Dict[str, Any] = self._client.head_object(
                Bucket=self.bucket, Key=self.object_key(key)
            )
        except Exception as exc:
            if _is_missing(exc):
                return None
            raise exceptions.ReadFileError(self._describe(key)) from exc
        return head

    def _current(self, key: str) -> bytes:
        """Read an object, treating a missing one as empty."""
        return self.read_bytes(key) if self.is_blob(key) else b""

    def _delete_batch(self, batch: List[Dict[str, str]]) -> None:
        """Remove up to a thousand objects in one call."""
        self._client.delete_objects(Bucket=self.bucket, Delete={"Objects": batch})

    def _describe(self, key: str) -> str:
        """Name a key the way an operator would recognise it."""
        return f"{self.location}/{key}"


def _is_missing(exc: BaseException) -> bool:
    """Determine whether an S3 error simply means "no such object"."""
    return _error_code(exc) in _MISSING_CODES


def _is_precondition_failure(exc: BaseException) -> bool:
    """Determine whether an S3 error means somebody else wrote first."""
    return _error_code(exc) in _PRECONDITION_CODES


def _error_code(exc: BaseException) -> str:
    """Extract the S3 error code out of a boto3 exception."""
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return ""
    code: str = response.get("Error", {}).get("Code", "")
    return code


def _build_client() -> Any:
    """Build an S3 client out of the environment.

    Credentials come from the standard boto3 resolution chain, so the usual
    ``AWS_*`` variables, shared config files and instance roles all work
    untouched. The variables read here only cover what that chain cannot
    express: which endpoint to talk to when the target is not AWS itself.

    :return: The boto3 S3 client.
    :raise:
        :PDBStoreException: boto3 is not installed.
    """
    try:
        # Imported here so that boto3 stays an optional dependency: a store on
        # a local filesystem must not require it.
        import boto3  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise exceptions.PDBStoreException(
            "boto3 is required to use an s3:// symbol store (pip install pdbstore[s3])"
        ) from exc

    from pdbstore import const  # pylint: disable=import-outside-toplevel

    session_args = {}
    profile = os.environ.get(const.ENV_PDBSTORE_S3_PROFILE)
    if profile:
        session_args["profile_name"] = profile
    region = os.environ.get(const.ENV_PDBSTORE_S3_REGION)
    if region:
        session_args["region_name"] = region

    client_args = {}
    endpoint = os.environ.get(const.ENV_PDBSTORE_S3_ENDPOINT_URL)
    if endpoint:
        client_args["endpoint_url"] = endpoint

    return boto3.session.Session(**session_args).client("s3", **client_args)

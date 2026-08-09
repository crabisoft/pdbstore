"""S3 behaviors the shared contract cannot express.

The contract suite states what every blob store owes its callers. What is left
here is what the object store protocol imposes on this one backend: a write can
fail for a reason that has nothing to do with contention, and a deletion is
capped at a thousand keys per request. Both are invisible on a small store and
certain on a real one.

Concurrent appends, the other object store specific, have a suite of their own
in :mod:`tests.contract.test_s3_concurrency`.

Unlike that one, this suite stays on the emulator. Its refusals come from a
client stub the server never sees, and its batch deletions write a couple of
thousand objects — over a network, that would buy wall-clock rather than
confidence.
"""

import pytest

pytest.importorskip("boto3")
pytest.importorskip("moto")

# pylint: disable=import-error,wrong-import-position
from botocore.exceptions import ClientError  # noqa: E402

from pdbstore import exceptions  # noqa: E402
from pdbstore.drivers.blob.s3 import _DELETE_BATCH, S3BlobStore  # noqa: E402

from .conftest import BUCKET  # noqa: E402


class RefusingClient:
    """An S3 client refusing every write, the way a read-only bucket would."""

    def __init__(self, client, code="AccessDenied"):
        self._client = client
        self._code = code
        self.attempts = 0

    def __getattr__(self, name):
        return getattr(self._client, name)

    def put_object(self, **_kwargs):
        """Refuse the write for a reason no retry could ever resolve."""
        self.attempts += 1
        raise ClientError(
            {"Error": {"Code": self._code, "Message": "denied"}},
            "PutObject",
        )


class CountingClient:
    """An S3 client recording the size of every batch deletion."""

    def __init__(self, client):
        self._client = client
        self.batches = []

    def __getattr__(self, name):
        return getattr(self._client, name)

    def delete_objects(self, **kwargs):
        """Record how many keys this request carries, then let it through."""
        self.batches.append(len(kwargs["Delete"]["Objects"]))
        return self._client.delete_objects(**kwargs)


def test_an_append_refused_outright_is_not_retried(s3_client):
    """A write failing for another reason than contention is reported at once.

    The retry loop exists to let a losing writer read the winner's version and
    try again. A denied write would never turn into a granted one, so retrying
    it would only turn a clear error into a slow one.
    """
    client = RefusingClient(s3_client)
    store = S3BlobStore(BUCKET, client=client, max_attempts=8)

    with pytest.raises(exceptions.WriteFileError) as failure:
        store.append_bytes("000Admin/server.txt", b"a line")

    assert client.attempts == 1
    assert "concurrent writers" not in str(failure.value)


def test_an_append_onto_an_existing_blob_reports_a_refusal(s3_client):
    """The same holds on the extension path, not only on creation."""
    S3BlobStore(BUCKET, client=s3_client).write_bytes("000Admin/server.txt", b"start")
    client = RefusingClient(s3_client)
    store = S3BlobStore(BUCKET, client=client)

    with pytest.raises(exceptions.WriteFileError):
        store.append_bytes("000Admin/server.txt", b"-more")

    assert client.attempts == 1
    # The failed append left the previous content untouched.
    assert S3BlobStore(BUCKET, client=s3_client).read_bytes("000Admin/server.txt") == b"start"


def test_deleting_more_keys_than_one_request_holds(s3_client):
    """A prefix wider than a batch is removed in several requests.

    ``DeleteObjects`` refuses more than a thousand keys at a time, and a symbol
    store holding a thousand files is an ordinary one. Deleting a transaction
    on such a store is exactly where an unflushed batch would drop keys.
    """
    client = CountingClient(s3_client)
    store = S3BlobStore(BUCKET, client=client)
    total = _DELETE_BATCH + 1
    for index in range(total):
        s3_client.put_object(Bucket=BUCKET, Key=f"drop/{index:05d}.pdb", Body=b"x")
    store.write_bytes("keep/file.txt", b"1")

    store.delete_prefix("drop")

    assert client.batches == [_DELETE_BATCH, 1]
    assert not list(store.list("drop"))
    assert store.read_bytes("keep/file.txt") == b"1"


def test_a_prefix_filling_exactly_one_batch_is_not_flushed_twice(s3_client):
    """A prefix landing on the batch boundary sends one request, not two."""
    client = CountingClient(s3_client)
    store = S3BlobStore(BUCKET, client=client)
    for index in range(_DELETE_BATCH):
        s3_client.put_object(Bucket=BUCKET, Key=f"drop/{index:05d}.pdb", Body=b"x")

    store.delete_prefix("drop")

    assert client.batches == [_DELETE_BATCH]
    assert not list(store.list("drop"))

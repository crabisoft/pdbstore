"""Concurrent appends against an object store.

The blob store contract requires an implementation backed by an object store to
make its read-modify-write appends safe against concurrent writers. S3 is the
only backend where that clause bites, and it is the one failure mode that would
be invisible in normal use and catastrophic in CI: two builds publishing at the
same moment, one transaction silently gone.

Each test drives a real interleaving — another writer commits in the window
between the read and the write — rather than asserting that the right flags
were passed.

This is the suite that matters most on a live server: an object store that
quietly ignores a conditional write passes everything else and loses a
transaction here. It therefore runs against the emulator and, when one is
offered, against the real thing.
"""

import pytest

from pdbstore import exceptions

pytest.importorskip("boto3")
pytest.importorskip("moto")

# pylint: disable=import-error,wrong-import-position
from pdbstore.drivers.blob.s3 import S3BlobStore  # noqa: E402

KEY = "000Admin/server.txt"


class RacingClient:
    """An S3 client that lets a competing writer slip in before each write.

    Reproduces the window an object store leaves open between reading an object
    and writing it back, which is where a lost update would happen.
    """

    def __init__(self, client, intruder, times=1):
        self._client = client
        self._intruder = intruder
        self._remaining = times

    def __getattr__(self, name):
        return getattr(self._client, name)

    def put_object(self, **kwargs):
        """Let the competing writer commit first, then attempt our own write."""
        if self._remaining > 0:
            self._remaining -= 1
            self._intruder()
        return self._client.put_object(**kwargs)


@pytest.fixture(name="stores")
def fixture_stores(s3_area):
    """Yield two stores over the same corner of a bucket, one of them racing."""

    def _build(intruder, times=1, conditional_writes=True):
        competitor = s3_area.store()
        racing = s3_area.store(
            client=RacingClient(s3_area.client, lambda: intruder(competitor), times),
            conditional_writes=conditional_writes,
        )
        return racing, competitor

    return _build


def test_a_concurrent_append_is_not_lost(stores):
    """Both writers' data survives when they append at the same moment."""
    racing, competitor = stores(lambda store: store.append_bytes(KEY, b"-B"))
    competitor.write_bytes(KEY, b"start")

    racing.append_bytes(KEY, b"-A")

    # The competitor got there first, so its line is kept and ours follows it.
    assert competitor.read_bytes(KEY) == b"start-B-A"


def test_the_guard_is_what_prevents_the_loss(stores):
    """Without the conditional write, the same interleaving loses a line.

    Pinned deliberately: it states what the guard is buying, and would start
    failing the day the guard is silently dropped.
    """
    racing, competitor = stores(
        lambda store: store.append_bytes(KEY, b"-B"), conditional_writes=False
    )
    competitor.write_bytes(KEY, b"start")

    racing.append_bytes(KEY, b"-A")

    assert competitor.read_bytes(KEY) == b"start-A"
    assert b"-B" not in competitor.read_bytes(KEY)


def test_a_concurrent_creation_is_not_lost(stores):
    """Two writers creating the same object at once keep both contributions."""
    racing, competitor = stores(lambda store: store.append_bytes(KEY, b"first"))

    racing.append_bytes(KEY, b"second")

    assert competitor.read_bytes(KEY) == b"firstsecond"


def test_repeated_contention_still_converges(stores):
    """An append survives losing the race several times in a row."""
    racing, competitor = stores(lambda store: store.append_bytes(KEY, b"x"), times=3)
    competitor.write_bytes(KEY, b"")

    racing.append_bytes(KEY, b"done")

    assert competitor.read_bytes(KEY) == b"xxxdone"


def test_endless_contention_is_reported_rather_than_looping(s3_area):
    """A writer that can never win gives up with a clear error."""
    competitor = s3_area.store()
    racing = s3_area.store(
        client=RacingClient(s3_area.client, lambda: competitor.append_bytes(KEY, b"x"), times=99),
        max_attempts=3,
    )

    with pytest.raises(exceptions.WriteFileError) as failure:
        racing.append_bytes(KEY, b"never")

    assert "concurrent writers" in str(failure.value)


def test_a_uri_names_the_bucket_and_prefix(s3_client):
    """An s3:// location resolves to the bucket and prefix it names."""
    store = S3BlobStore.from_uri("s3://a-bucket/team/symbols", client=s3_client)

    assert store.bucket == "a-bucket"
    assert store.prefix == "team/symbols"
    assert store.location == "s3://a-bucket/team/symbols"
    assert store.object_key("foo.pdb/ABC/foo.pdb") == "team/symbols/foo.pdb/ABC/foo.pdb"


def test_a_uri_without_a_bucket_is_rejected(s3_client):
    """A location naming no bucket fails rather than writing somewhere odd."""
    with pytest.raises(exceptions.PDBStoreException):
        S3BlobStore.from_uri("s3://", client=s3_client)


def test_two_prefixes_share_a_bucket_without_colliding(s3_area):
    """Two stores in one bucket stay independent."""
    first = S3BlobStore(s3_area.bucket, prefix=f"{s3_area.prefix}/release", client=s3_area.client)
    second = S3BlobStore(s3_area.bucket, prefix=f"{s3_area.prefix}/snapshot", client=s3_area.client)

    first.write_bytes("k.txt", b"one")
    second.write_bytes("k.txt", b"two")

    assert first.read_bytes("k.txt") == b"one"
    assert second.read_bytes("k.txt") == b"two"
    assert list(first.list("")) == ["k.txt"]

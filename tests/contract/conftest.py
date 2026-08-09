"""Backends submitted to the contract suites.

Registering a backend here is what makes the whole contract run against it, and
that is the entire integration cost of a new one: everything the rest of the
code relies on is verified from these fixtures alone.

S3 is exercised twice. ``s3`` runs against ``moto``, which emulates the parts
that actually matter here — conditional writes, suffix ranges, batch deletes —
rather than stubbing them out, and needs nothing but a pip install. ``live-s3``
replays the very same suite against a server that is really listening, which is
the only way to find out whether an implementation honours the conditional
writes the append relies on; it is skipped, visibly, until
``PDBSTORE_TEST_S3_ENDPOINT`` points at one.
"""

import os
import re

import pytest

from pdbstore.adapters.symsrv import SymSrvGateway
from pdbstore.drivers.blob import LocalBlobStore, MemoryBlobStore
from pdbstore.drivers.compression import CabCompressor

BUCKET = "pdbstore-contract"

ENV_LIVE_ENDPOINT = "PDBSTORE_TEST_S3_ENDPOINT"
"""Where a real object store is listening. Absent means "do not run those"."""

ENV_LIVE_BUCKET = "PDBSTORE_TEST_S3_BUCKET"
"""Bucket to work in on that server. Created when missing."""

BACKENDS = ["local", "memory", "s3", "live-s3"]
"""Every backend the contract is replayed against."""

S3_FLAVOURS = ["s3", "live-s3"]
"""The two ways the S3 backend itself is exercised: emulated, then for real."""


class S3Area:
    """A corner of an object store nothing else writes to.

    A live server keeps what a test leaves behind, so each test is given a key
    prefix of its own rather than the whole bucket. Handing that prefix around
    together with the client is what lets one suite serve both flavours.
    """

    def __init__(self, client, bucket, prefix):
        self.client = client
        self.bucket = bucket
        self.prefix = prefix

    def store(self, client=None, **kwargs):
        """Build a store over this corner.

        :param client: Client to go through, when a test needs to interpose on
            the requests. Defaults to the one the area was opened with.
        :param kwargs: Extra arguments forwarded to the constructor.
        """
        from pdbstore.drivers.blob.s3 import (  # pylint: disable=import-outside-toplevel
            S3BlobStore,
        )

        return S3BlobStore(
            self.bucket,
            prefix=self.prefix,
            client=self.client if client is None else client,
            **kwargs,
        )


@pytest.fixture(name="s3_client")
def fixture_s3_client():
    """Yield a client on an emulated, empty bucket."""
    boto3 = pytest.importorskip("boto3")
    moto = pytest.importorskip("moto")

    with moto.mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


@pytest.fixture(name="live_s3")
def fixture_live_s3(request):
    """Yield a clean corner of a real object store, or skip when none is given.

    Credentials are left to the usual boto3 chain, so the ``AWS_*`` variables
    work here exactly as they do in production. Only the endpoint is ours to
    supply: it is what tells the client to talk to MinIO or Ceph instead of AWS.
    """
    endpoint = os.environ.get(ENV_LIVE_ENDPOINT)
    if not endpoint:
        pytest.skip(f"set {ENV_LIVE_ENDPOINT} to replay this against a real object store")
    boto3 = pytest.importorskip("boto3")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )
    bucket = os.environ.get(ENV_LIVE_BUCKET, BUCKET)
    _ensure_bucket(client, bucket)

    area = S3Area(client, bucket, _prefix_for(request.node))
    _wipe(client, bucket, area.prefix)
    yield area
    _wipe(client, bucket, area.prefix)


@pytest.fixture(name="s3_area", params=S3_FLAVOURS)
def fixture_s3_area(request):
    """Yield the same clean corner, emulated and then real."""
    if request.param == "s3":
        return S3Area(request.getfixturevalue("s3_client"), BUCKET, "")
    return request.getfixturevalue("live_s3")


def build_blob_store(kind, tmp_path, client=None, name="blobs"):
    """Build one blob store of the requested kind.

    :param kind: One of ``local``, ``memory`` or ``s3``.
    :param tmp_path: Directory the local backend may use.
    :param client: The emulated S3 client, for the ``s3`` backend.
    :param name: Distinguishes two stores living side by side.
    """
    if kind == "local":
        rootdir = tmp_path / name
        rootdir.mkdir(parents=True, exist_ok=True)
        return LocalBlobStore(rootdir)
    if kind == "memory":
        return MemoryBlobStore(name)

    from pdbstore.drivers.blob.s3 import (  # pylint: disable=import-outside-toplevel
        S3BlobStore,
    )

    return S3BlobStore(BUCKET, prefix=name, client=client)


def _for_backend(request, tmp_path, name):
    """Build the backend named by the current parameter.

    Neither the emulated bucket nor the live one is reached for unless the run
    calls for it, so the other backends stay free of both and the suite still
    runs when boto3 is absent.
    """
    if request.param == "s3":
        return build_blob_store("s3", tmp_path, request.getfixturevalue("s3_client"), name)
    if request.param == "live-s3":
        area = request.getfixturevalue("live_s3")
        return S3Area(area.client, area.bucket, f"{area.prefix}/{name}").store()
    return build_blob_store(request.param, tmp_path, name=name)


@pytest.fixture(params=BACKENDS)
def blob_store(request, tmp_path):
    """Yield each blob store implementation in turn."""
    return _for_backend(request, tmp_path, "blobs")


@pytest.fixture
def other_blob_store(tmp_path):
    """Yield a second, independent blob store to migrate into."""
    rootdir = tmp_path / "other-blobs"
    rootdir.mkdir(parents=True, exist_ok=True)
    return LocalBlobStore(rootdir)


@pytest.fixture(params=BACKENDS)
def symbol_store(request, tmp_path):
    """Yield the symbol store gateway over each blob store implementation."""
    return SymSrvGateway(_for_backend(request, tmp_path, "store"), CabCompressor())


def _ensure_bucket(client, bucket):
    """Create the working bucket unless the server already holds it."""
    try:
        client.create_bucket(Bucket=bucket)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
        if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise


def _prefix_for(node):
    """Name a corner of the bucket after the test that works in it."""
    path, _, name = node.nodeid.partition("::")
    module = os.path.splitext(os.path.basename(path))[0]
    return f"{module}/{re.sub(r'[^A-Za-z0-9_.-]+', '-', name).strip('-')}"


def _wipe(client, bucket, prefix):
    """Empty a corner of the bucket, so a test starts from nothing."""
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix + "/"):
        keys = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if keys:
            client.delete_objects(Bucket=bucket, Delete={"Objects": keys})

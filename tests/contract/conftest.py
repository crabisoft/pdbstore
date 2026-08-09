"""Backends submitted to the contract suites.

Registering a backend here is what makes the whole contract run against it, and
that is the entire integration cost of a new one: everything the rest of the
code relies on is verified from these fixtures alone.

S3 is exercised against ``moto``, which emulates the parts that actually matter
here — conditional writes, suffix ranges, batch deletes — rather than being
stubbed out.
"""

import pytest

from pdbstore.adapters.symsrv import SymSrvGateway
from pdbstore.drivers.blob import LocalBlobStore, MemoryBlobStore
from pdbstore.drivers.compression import CabCompressor

BUCKET = "pdbstore-contract"

BACKENDS = ["local", "memory", "s3"]


@pytest.fixture(name="s3_client")
def fixture_s3_client():
    """Yield a client on an emulated, empty bucket."""
    boto3 = pytest.importorskip("boto3")
    moto = pytest.importorskip("moto")

    with moto.mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


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

    The emulated bucket is only spun up for the S3 run, so the other backends
    stay free of it and the suite still runs when boto3 is absent.
    """
    if request.param != "s3":
        return build_blob_store(request.param, tmp_path, name=name)
    return build_blob_store("s3", tmp_path, request.getfixturevalue("s3_client"), name)


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

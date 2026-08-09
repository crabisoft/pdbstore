"""Backends submitted to the contract suites.

Registering a backend here is what makes the whole contract run against it.
When ``S3BlobStore`` lands, adding one entry to ``BLOB_STORES`` is the entire
integration work — everything the rest of the code relies on is then verified
against it.
"""

import pytest

from pdbstore.adapters.symsrv import SymSrvGateway
from pdbstore.drivers.blob import LocalBlobStore, MemoryBlobStore
from pdbstore.drivers.compression import CabCompressor


@pytest.fixture(params=["local", "memory"])
def blob_store(request, tmp_path):
    """Yield each blob store implementation in turn."""
    if request.param == "local":
        rootdir = tmp_path / "blobs"
        rootdir.mkdir(parents=True, exist_ok=True)
        return LocalBlobStore(rootdir)
    return MemoryBlobStore()


@pytest.fixture
def other_blob_store(tmp_path):
    """Yield a second, independent blob store to migrate into."""
    rootdir = tmp_path / "other-blobs"
    rootdir.mkdir(parents=True, exist_ok=True)
    return LocalBlobStore(rootdir)


@pytest.fixture(params=["local", "memory"])
def symbol_store(request, tmp_path):
    """Yield the symbol store gateway over each blob store implementation."""
    if request.param == "local":
        rootdir = tmp_path / "store"
        rootdir.mkdir(parents=True, exist_ok=True)
        return SymSrvGateway(LocalBlobStore(rootdir), CabCompressor())
    return SymSrvGateway(MemoryBlobStore(), CabCompressor())

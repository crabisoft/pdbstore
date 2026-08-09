"""Resolution of a store location into a backend."""

import builtins
import sys

import pytest

from pdbstore.drivers.blob import LocalBlobStore, MemoryBlobStore
from pdbstore.drivers.blob.factory import create_blob_store, supported_schemes
from pdbstore.exceptions import PDBStoreException


def test_a_plain_path_stays_local(tmp_path):
    """A location with no scheme names a directory."""
    store = create_blob_store(tmp_path)

    assert isinstance(store, LocalBlobStore)
    assert store.rootdir == tmp_path


def test_a_windows_drive_is_not_a_scheme():
    """``C:\\symbols`` is a path, not a URI, despite the colon."""
    store = create_blob_store("C:\\symbols")

    assert isinstance(store, LocalBlobStore)


@pytest.mark.parametrize(
    "location",
    ["file:///var/symbols", "memory://scratch"],
)
def test_registered_schemes_resolve(location):
    """Every advertised scheme builds a store."""
    assert create_blob_store(location) is not None


def test_a_memory_uri_names_its_store():
    """An in-memory store carries the name given in its URI."""
    store = create_blob_store("memory://scratch")

    assert isinstance(store, MemoryBlobStore)
    assert store.location == "memory://scratch"


def test_an_unknown_scheme_lists_the_known_ones():
    """An unsupported location says what would have been supported."""
    with pytest.raises(PDBStoreException) as failure:
        create_blob_store("ftp://host/symbols")

    message = str(failure.value)
    assert "ftp" in message
    for scheme in supported_schemes():
        assert scheme in message


def test_s3_stays_optional(monkeypatch, tmp_path):
    """A local store works on an installation without boto3.

    boto3 is an extra, so importing it eagerly would make every user of a
    local store pay for a dependency they do not need. Only reaching for an
    ``s3://`` location may fail, and it must say how to fix it.
    """
    real_import = builtins.__import__

    def without_boto3(name, *args, **kwargs):
        if name == "boto3" or name.startswith("boto3."):
            raise ImportError("No module named 'boto3'")
        return real_import(name, *args, **kwargs)

    for module in [name for name in sys.modules if name.startswith("boto")]:
        monkeypatch.delitem(sys.modules, module)
    monkeypatch.setattr(builtins, "__import__", without_boto3)

    assert isinstance(create_blob_store(tmp_path), LocalBlobStore)

    with pytest.raises(PDBStoreException) as failure:
        create_blob_store("s3://bucket/prefix")

    assert "pdbstore[s3]" in str(failure.value)

"""Migration between two storage backends.

The claim these tests defend is the one the whole arrangement rests on: because
every backend lays a store out identically, moving one is a copy of keys, and
the destination is indistinguishable from the source.
"""

import pytest

from pdbstore.adapters.symsrv import SymSrvGateway
from pdbstore.drivers.blob import LocalBlobStore, MemoryBlobStore
from pdbstore.drivers.compression import CabCompressor
from pdbstore.drivers.parsing import PdbSymbolFileReader
from pdbstore.entities import OpStatus
from pdbstore.usecases.add import AddSymbolsInteractor
from pdbstore.usecases.query import QuerySymbolsInteractor
from pdbstore.usecases.storage import MigrateStorageInteractor, VerifyStorageInteractor
from pdbstore.usecases.store_state import StoreState


@pytest.fixture(name="populated")
def fixture_populated(tmp_path, test_data_native_dir):
    """Build a store holding one committed transaction."""
    blob = LocalBlobStore(tmp_path / "source")
    state = StoreState(SymSrvGateway(blob, CabCompressor()), PdbSymbolFileReader())
    summary = AddSymbolsInteractor(state).execute(
        [test_data_native_dir / "dummyapp.pdb"], "myproduct", "1.0"
    )
    assert summary.status == OpStatus.SUCCESS
    return blob


def test_migration_reproduces_every_key(populated):
    """The target ends up holding exactly what the source held."""
    target = MemoryBlobStore()

    summary = MigrateStorageInteractor(populated, target).execute()

    assert summary.status == OpStatus.SUCCESS
    assert sorted(target.list("")) == sorted(populated.list(""))
    for key in populated.list(""):
        assert target.read_bytes(key) == populated.read_bytes(key)


def test_dry_run_writes_nothing(populated):
    """A dry run reports the work without performing it."""
    target = MemoryBlobStore()

    summary = MigrateStorageInteractor(populated, target).execute(dry_run=True)

    assert summary.success() > 0
    assert not list(target.list(""))


def test_migration_resumes_without_redoing_the_work(populated):
    """Running a migration again skips what already made it across."""
    target = MemoryBlobStore()
    MigrateStorageInteractor(populated, target).execute()

    summary = MigrateStorageInteractor(populated, target).execute()

    assert summary.success() == 0
    assert summary.skipped() > 0


def test_verification_confirms_a_complete_migration(populated):
    """Verification passes once the target holds everything."""
    target = MemoryBlobStore()
    MigrateStorageInteractor(populated, target).execute()

    summary = VerifyStorageInteractor(populated, target).execute(deep=True)

    assert summary.status == OpStatus.SUCCESS
    assert summary.failed() == 0


def test_verification_catches_a_missing_key(populated):
    """Verification fails when the target is short of a key."""
    target = MemoryBlobStore()
    MigrateStorageInteractor(populated, target).execute()
    target.delete(next(iter(target.list(""))))

    summary = VerifyStorageInteractor(populated, target).execute()

    assert summary.status == OpStatus.FAILED
    assert summary.failed() > 0


def test_verification_catches_altered_content(populated):
    """A deep verification notices content that differs at equal size."""
    target = MemoryBlobStore()
    MigrateStorageInteractor(populated, target).execute()
    key = next(key for key in target.list("") if key.endswith(".pdb"))
    target.write_bytes(key, b"\x00" * len(target.read_bytes(key)))

    shallow = VerifyStorageInteractor(populated, target).execute()
    deep = VerifyStorageInteractor(populated, target).execute(deep=True)

    # Same size, so only the deep comparison can tell them apart.
    assert shallow.status == OpStatus.SUCCESS
    assert deep.status == OpStatus.FAILED


def test_a_migrated_store_serves_the_same_answers(populated, test_data_native_dir):
    """The migrated store answers queries exactly as the original did."""
    target = MemoryBlobStore()
    MigrateStorageInteractor(populated, target).execute()

    files = [test_data_native_dir / "dummyapp.pdb"]
    before = QuerySymbolsInteractor(
        StoreState(SymSrvGateway(populated, CabCompressor()), PdbSymbolFileReader())
    ).execute(files)
    after = QuerySymbolsInteractor(
        StoreState(SymSrvGateway(target, CabCompressor()), PdbSymbolFileReader())
    ).execute(files)

    assert before.status == after.status
    assert [item["path"] for item in before.files] == [item["path"] for item in after.files]
    assert after.success() == 1

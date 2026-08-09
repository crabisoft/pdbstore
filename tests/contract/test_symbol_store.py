"""Contract every SymbolStoreGateway implementation must satisfy.

Written against the interface only, so it holds whatever blob store ends up
underneath. A backend passing both this and the blob store contract can serve
every interactor without any of them being aware of the change.
"""

import datetime

import pytest

from pdbstore.entities import symsrv_layout
from pdbstore.entities.entry import TransactionEntry
from pdbstore.entities.transaction import Transaction
from pdbstore.entities.transaction_type import TransactionType


@pytest.fixture(name="source_file")
def fixture_source_file(tmp_path):
    """Create a local file to be stored as a symbol."""
    path = tmp_path / "dummy.pdb"
    path.write_bytes(b"symbol-content")
    return path


def _entry(source_file, compressed=False):
    """Build an entry pointing at a local file."""
    return TransactionEntry("dummy.pdb", "ABCDEF0123456789", source_file, compressed)


def _transaction(gateway, transaction_id=None):
    """Build a transaction bound to a gateway."""
    return Transaction(
        transaction_id,
        TransactionType.ADD,
        product="myproduct",
        version="1.0",
        comment="a comment",
        binding=gateway,
    )


def test_location_is_reported(symbol_store):
    """A store describes where it keeps its data."""
    assert symbol_store.location
    assert isinstance(symbol_store.display_path(symsrv_layout.server_key()), str)


def test_identifiers_start_at_one_and_are_stable(symbol_store):
    """An empty store hands out the first identifier, and keeps handing it out."""
    symbol_store.prepare()

    assert symbol_store.next_transaction_id == "0000000001"
    # Peeking does not consume: until a transaction is committed, the same
    # identifier is offered again.
    assert symbol_store.next_transaction_id == "0000000001"


def test_identifiers_advance_once_committed(symbol_store):
    """Recording an identifier makes the next one follow it."""
    symbol_store.prepare()
    symbol_store.commit_transaction_id(symbol_store.next_transaction_id)

    assert symbol_store.next_transaction_id == "0000000002"


def test_committing_an_empty_identifier_is_rejected(symbol_store):
    """An empty identifier is a programming error, not a no-op."""
    symbol_store.prepare()

    with pytest.raises(Exception):
        symbol_store.commit_transaction_id("")


def test_transactions_round_trip(symbol_store):
    """A listed transaction is read back with its attributes intact."""
    symbol_store.prepare()
    transaction = _transaction(symbol_store, "0000000001")
    transaction.timestamp = datetime.datetime(2024, 5, 1, 12, 30, 45)

    symbol_store.append_transaction(transaction)
    loaded = symbol_store.load_transactions()

    assert list(loaded) == ["0000000001"]
    assert loaded["0000000001"].product == "myproduct"
    assert loaded["0000000001"].version == "1.0"
    assert loaded["0000000001"].comment == "a comment"


def test_an_empty_store_lists_nothing(symbol_store):
    """A store that was never written to holds no transaction and no history."""
    assert symbol_store.load_transactions() == {}
    assert symbol_store.load_history() == []


def test_rewriting_replaces_the_listing(symbol_store):
    """Rewriting the listing drops the transactions left out of it."""
    symbol_store.prepare()

    first = _transaction(symbol_store, "0000000001")
    first.timestamp = datetime.datetime(2024, 5, 1, 12, 0, 0)
    second = _transaction(symbol_store, "0000000002")
    second.timestamp = datetime.datetime(2024, 5, 2, 12, 0, 0)
    symbol_store.append_transaction(first)
    symbol_store.append_transaction(second)

    symbol_store.rewrite_transactions([second])

    assert list(symbol_store.load_transactions()) == ["0000000002"]


def test_history_lines_stay_separated(symbol_store):
    """Successive history entries never end up glued together."""
    symbol_store.prepare()

    symbol_store.append_history("0000000001,del,0000000000")
    symbol_store.append_history("0000000002,del,0000000001")

    history = symbol_store.load_history()
    assert [item.id for item in history] == ["0000000001", "0000000002"]


def test_entries_round_trip(symbol_store, source_file):
    """The files referenced by a transaction are read back as they were written."""
    symbol_store.prepare()
    transaction = _transaction(symbol_store, "0000000001")
    transaction.add_entry(_entry(source_file))

    symbol_store.write_entries(transaction)
    loaded = symbol_store.load_entries(transaction)

    assert len(loaded) == 1
    assert loaded[0].file_name == "dummy.pdb"
    assert loaded[0].file_hash == "ABCDEF0123456789"


def test_an_uncommitted_transaction_references_nothing(symbol_store):
    """Entries cannot be resolved before the transaction has an identifier."""
    assert symbol_store.load_entries(_transaction(symbol_store)) == []


def test_storing_an_entry_makes_it_readable(symbol_store, source_file):
    """A stored entry exists, reports a size, and serves its content back."""
    symbol_store.prepare()
    entry = _entry(source_file)

    assert symbol_store.entry_exists(entry) is False
    assert symbol_store.store_entry(entry) is True
    assert symbol_store.entry_exists(entry) is True

    stat = symbol_store.entry_stat(entry)
    assert stat is not None
    assert stat.size == len(b"symbol-content")

    stream = symbol_store.open_entry(entry.stored_key)
    try:
        assert stream.read() == b"symbol-content"
    finally:
        stream.close()


def test_storing_an_existing_entry_is_reported_honestly(symbol_store, source_file):
    """Re-storing reports success, unless the caller asked to skip duplicates."""
    symbol_store.prepare()
    entry = _entry(source_file)
    symbol_store.store_entry(entry)

    assert symbol_store.store_entry(entry) is True
    assert symbol_store.store_entry(entry, skip_if_exists=True) is False


def test_extracting_an_entry_writes_it_out(symbol_store, source_file, tmp_path):
    """An extracted entry lands under its original name."""
    symbol_store.prepare()
    entry = _entry(source_file)
    symbol_store.store_entry(entry)

    destination = tmp_path / "out"
    destination.mkdir()
    extracted = symbol_store.extract_entry(entry, destination)

    assert (destination / "dummy.pdb").read_bytes() == b"symbol-content"
    assert str(extracted).endswith("dummy.pdb")


def test_entry_content_can_be_released(symbol_store, source_file):
    """Releasing an entry removes its content and says whether it did."""
    symbol_store.prepare()
    entry = _entry(source_file)
    symbol_store.store_entry(entry)

    assert symbol_store.has_entry_content(entry.dir_key) is True
    assert symbol_store.delete_entry_content(entry.dir_key) is True
    assert symbol_store.has_entry_content(entry.dir_key) is False
    # Releasing what is already gone reports that nothing was removed.
    assert symbol_store.delete_entry_content(entry.dir_key) is False


def test_uncompressed_entries_are_not_reported_as_compressed(symbol_store, source_file):
    """Compression is a property of how the symbol was stored."""
    symbol_store.prepare()
    entry = _entry(source_file)
    symbol_store.store_entry(entry)

    assert symbol_store.is_entry_compressed("dummy.pdb", "ABCDEF0123456789") is False


def test_marking_a_transaction_deleted(symbol_store, source_file):
    """A deleted transaction is flagged, and stops being readable as active."""
    symbol_store.prepare()
    transaction = _transaction(symbol_store, "0000000001")
    transaction.add_entry(_entry(source_file))
    symbol_store.write_entries(transaction)

    assert symbol_store.is_deleted(transaction) is False
    symbol_store.mark_deleted(transaction)
    assert symbol_store.is_deleted(transaction) is True


def test_marking_a_transaction_promoted(symbol_store, source_file):
    """A promoted transaction is flagged but stays readable."""
    symbol_store.prepare()
    transaction = _transaction(symbol_store, "0000000001")
    transaction.add_entry(_entry(source_file))
    symbol_store.write_entries(transaction)

    assert symbol_store.is_promoted(transaction) is False
    symbol_store.mark_promoted(transaction)
    assert symbol_store.is_promoted(transaction) is True
    assert symbol_store.is_deleted(transaction) is False


def test_marking_an_unknown_transaction_is_survivable(symbol_store):
    """Marking a transaction that was never written warns rather than raising."""
    symbol_store.prepare()
    transaction = _transaction(symbol_store, "0000009999")

    symbol_store.mark_deleted(transaction)
    symbol_store.mark_promoted(transaction)

    assert symbol_store.is_deleted(transaction) is False


def test_reset_forgets_cached_identifiers(symbol_store):
    """Resetting makes the store re-read what it had cached."""
    symbol_store.prepare()
    assert symbol_store.next_transaction_id == "0000000001"
    symbol_store.commit_transaction_id("0000000042")

    symbol_store.reset()

    assert symbol_store.next_transaction_id == "0000000043"

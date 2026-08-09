"""Contract every BlobStore implementation must satisfy.

This suite is the definition of what "being a blob store" means for pdbstore.
It is deliberately written against the interface only: any backend passing it
can host a symbol store, and any backend failing it will break the SymSrv
gateway in a way that is far harder to diagnose from the outside.
"""

import io

import pytest

from pdbstore import exceptions


def test_location_is_reported(blob_store):
    """A store describes where it keeps its data."""
    assert blob_store.location
    assert isinstance(blob_store.location, str)


def test_missing_key_reads_as_absent(blob_store):
    """Nothing is stored under a key that was never written."""
    assert blob_store.exists("absent.txt") is False
    assert blob_store.is_blob("absent.txt") is False
    assert blob_store.stat("absent.txt") is None
    assert blob_store.read_tail("absent.txt", 4) == b""
    assert not list(blob_store.list("absent"))


def test_write_then_read_round_trips(blob_store):
    """What is written is what is read back."""
    blob_store.write_bytes("a/b/c.txt", b"hello")

    assert blob_store.exists("a/b/c.txt") is True
    assert blob_store.is_blob("a/b/c.txt") is True
    assert blob_store.read_bytes("a/b/c.txt") == b"hello"


def test_write_replaces_previous_content(blob_store):
    """Writing an existing key replaces it rather than extending it."""
    blob_store.write_bytes("k.txt", b"first")
    blob_store.write_bytes("k.txt", b"second")

    assert blob_store.read_bytes("k.txt") == b"second"


def test_append_extends_and_creates(blob_store):
    """Appending extends an existing blob and creates a missing one."""
    blob_store.append_bytes("log.txt", b"one")
    blob_store.append_bytes("log.txt", b"two")

    assert blob_store.read_bytes("log.txt") == b"onetwo"


def test_stat_reports_the_size(blob_store):
    """The reported size is the number of bytes stored."""
    blob_store.write_bytes("k.txt", b"12345")

    stat = blob_store.stat("k.txt")
    assert stat is not None
    assert stat.size == 5
    assert stat.mtime > 0
    assert stat.atime > 0


def test_read_tail_returns_trailing_bytes(blob_store):
    """The tail is served without transferring the whole blob.

    The SymSrv history relies on this to decide whether it must insert a
    separator before appending.
    """
    blob_store.write_bytes("k.txt", b"abcdef")

    assert blob_store.read_tail("k.txt", 2) == b"ef"
    # Asking for more than the blob holds yields the whole blob.
    assert blob_store.read_tail("k.txt", 100) == b"abcdef"


def test_reading_a_missing_blob_is_an_error(blob_store):
    """Reading what is not there fails rather than returning empty content."""
    with pytest.raises(exceptions.ReadFileError):
        blob_store.read_bytes("absent.txt")


def test_exists_matches_containers_but_is_blob_does_not(blob_store):
    """A key holding other keys exists without holding content of its own."""
    blob_store.write_bytes("dir/inner.txt", b"x")

    assert blob_store.exists("dir") is True
    assert blob_store.is_blob("dir") is False


def test_list_walks_the_whole_prefix(blob_store):
    """Listing reports every key below a prefix, at any depth."""
    blob_store.write_bytes("p/one.txt", b"1")
    blob_store.write_bytes("p/deep/two.txt", b"2")
    blob_store.write_bytes("q/three.txt", b"3")

    assert sorted(blob_store.list("p")) == ["p/deep/two.txt", "p/one.txt"]
    assert sorted(blob_store.list("")) == [
        "p/deep/two.txt",
        "p/one.txt",
        "q/three.txt",
    ]


def test_streams_round_trip(blob_store):
    """Content can be moved through streams, never held whole in memory."""
    blob_store.write_stream("k.bin", io.BytesIO(b"streamed"))

    stream = blob_store.open_stream("k.bin")
    try:
        assert stream.read() == b"streamed"
    finally:
        stream.close()


def test_files_round_trip(blob_store, tmp_path):
    """Content can be moved to and from a local file."""
    source = tmp_path / "source.bin"
    source.write_bytes(b"payload")

    blob_store.put_file(source, "k.bin")
    assert blob_store.read_bytes("k.bin") == b"payload"

    target = tmp_path / "target.bin"
    blob_store.get_file("k.bin", target)
    assert target.read_bytes() == b"payload"


def test_copy_duplicates_and_move_relocates(blob_store):
    """Copying leaves the source in place; moving does not."""
    blob_store.write_bytes("src.txt", b"data")

    blob_store.copy("src.txt", "copy.txt")
    assert blob_store.read_bytes("copy.txt") == b"data"
    assert blob_store.is_blob("src.txt") is True

    blob_store.move("src.txt", "moved.txt")
    assert blob_store.read_bytes("moved.txt") == b"data"
    assert blob_store.is_blob("src.txt") is False


def test_delete_is_idempotent(blob_store):
    """Deleting an absent key is not an error."""
    blob_store.write_bytes("k.txt", b"x")

    blob_store.delete("k.txt")
    blob_store.delete("k.txt")

    assert blob_store.is_blob("k.txt") is False


def test_delete_prefix_removes_the_whole_subtree(blob_store):
    """Deleting a prefix removes every key below it and nothing else."""
    blob_store.write_bytes("keep/file.txt", b"1")
    blob_store.write_bytes("drop/a.txt", b"2")
    blob_store.write_bytes("drop/deep/b.txt", b"3")

    blob_store.delete_prefix("drop")

    assert not list(blob_store.list("drop"))
    assert blob_store.read_bytes("keep/file.txt") == b"1"


def test_make_container_allows_writing_below_it(blob_store):
    """Preparing a prefix is safe to call, and safe to call twice."""
    blob_store.make_container("some/deep/prefix")
    blob_store.make_container("some/deep/prefix")

    blob_store.write_bytes("some/deep/prefix/k.txt", b"x")
    assert blob_store.read_bytes("some/deep/prefix/k.txt") == b"x"


def test_local_path_is_either_usable_or_absent(blob_store):
    """A backend either offers a real local path, or admits it has none."""
    blob_store.write_bytes("k.txt", b"x")

    local = blob_store.local_path("k.txt")
    if local is not None:
        assert local.read_bytes() == b"x"

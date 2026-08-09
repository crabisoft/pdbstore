"""Move a symbol store from one storage backend to another.

Every backend lays a store out identically, so migrating is a copy of keys
rather than a replay of transactions. Nothing is parsed, nothing is
re-serialised, and there is therefore no way for the copy to drift from the
original — the destination is byte for byte what the source was.

These interactors are the reason
:class:`BlobStore <pdbstore.usecases.gateways.blob_store.BlobStore>` is a
gateway of its own: here the keys genuinely are the subject matter.
"""

from pdbstore.entities.summary import OpStatus, Summary
from pdbstore.exceptions import PDBStoreException
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import Iterator
from pdbstore.usecases.gateways.blob_store import BlobStore

__all__ = ["MigrateStorageInteractor", "transfer_blob"]


def transfer_blob(source: BlobStore, target: BlobStore, key: str) -> None:
    """Copy one blob across two stores, whatever their backends.

    The content is streamed rather than read whole, since a single symbol file
    can be larger than the memory available.

    :param source: The store holding the blob.
    :param target: The store receiving the blob.
    :param key: The key to be transferred.
    :raise:
        :ReadFileError: The blob cannot be read.
        :WriteFileError: The blob cannot be written.
    """
    stream = source.open_stream(key)
    try:
        target.write_stream(key, stream)
    finally:
        stream.close()


class MigrateStorageInteractor:
    """Copy every blob of a store into another store."""

    def __init__(self, source: BlobStore, target: BlobStore):
        self.source = source
        self.target = target

    def execute(
        self,
        dry_run: bool = False,
        overwrite: bool = False,
        prefix: str = "",
    ) -> Summary:
        """Transfer the content of the source store into the target store.

        Already transferred keys are skipped unless ``overwrite`` is set, so an
        interrupted migration is resumed simply by running it again.

        :param dry_run: True to report what would be transferred without
            writing anything.
        :param overwrite: True to transfer keys already present in the target.
        :param prefix: Optional key prefix to restrict the migration to.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object.
        """
        output = PDBStoreOutput()
        summary = Summary(None, OpStatus.SUCCESS)

        output.info(
            f"Migrating {self.source.location} to {self.target.location}"
            f"{' (dry run)' if dry_run else ''} ..."
        )

        for key in self._keys(prefix):
            if not overwrite and self.target.is_blob(key):
                summary.add_file(key, OpStatus.SKIPPED, "Already present")
                continue
            if dry_run:
                summary.add_file(key, OpStatus.SUCCESS)
                continue
            try:
                transfer_blob(self.source, self.target, key)
                summary.add_file(key, OpStatus.SUCCESS)
            except PDBStoreException as exc:
                summary.status = OpStatus.FAILED
                summary.add_file(key, OpStatus.FAILED, str(exc))
                output.error(f"failed to transfer {key}: {exc}")

        return summary

    def _keys(self, prefix: str) -> Iterator[str]:
        """Iterate over the keys to be transferred."""
        return self.source.list(prefix)

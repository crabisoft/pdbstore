"""Check that a migrated symbol store really holds everything."""

from pdbstore.entities.summary import OpStatus, Summary
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import List, Optional, Set
from pdbstore.usecases.gateways.blob_store import BlobStore

__all__ = ["VerifyStorageInteractor"]


class VerifyStorageInteractor:
    """Compare two stores key by key.

    Meant to be run before decommissioning the old backend: it answers whether
    the new one really holds everything, rather than assuming a migration that
    reported no error transferred everything.
    """

    def __init__(self, source: BlobStore, target: BlobStore):
        self.source = source
        self.target = target

    def execute(self, prefix: str = "", deep: bool = False) -> Summary:
        """Check that the target store holds everything the source does.

        :param prefix: Optional key prefix to restrict the comparison to.
        :param deep: True to compare the content of each blob rather than only
            its presence and size. Conclusive, but it transfers both stores in
            full, so it is off by default.
        :return: A :class:`Summary <pdbstore.entities.summary.Summary>` object,
            failed as soon as one key is missing or differs.
        """
        output = PDBStoreOutput()
        summary = Summary(None, OpStatus.SUCCESS)

        output.info(f"Verifying {self.target.location} against {self.source.location} ...")

        seen: Set[str] = set()
        for key in self.source.list(prefix):
            seen.add(key)
            error = self._compare(key, deep)
            if error is None:
                summary.add_file(key, OpStatus.SUCCESS)
            else:
                summary.status = OpStatus.FAILED
                summary.add_file(key, OpStatus.FAILED, error)

        # Keys the target holds on its own are reported but not treated as a
        # failure: a target may legitimately be a superset of the source.
        extra: List[str] = [key for key in self.target.list(prefix) if key not in seen]
        for key in extra:
            summary.add_file(key, OpStatus.SKIPPED, "Present in target only")

        return summary

    def _compare(self, key: str, deep: bool) -> Optional[str]:
        """Compare one key across both stores, returning the mismatch if any."""
        target_stat = self.target.stat(key)
        if target_stat is None:
            return "Missing from target"

        source_stat = self.source.stat(key)
        if source_stat is not None and source_stat.size != target_stat.size:
            return f"Size differs: {source_stat.size} vs {target_stat.size}"

        if deep and self.source.read_bytes(key) != self.target.read_bytes(key):
            return "Content differs"

        return None

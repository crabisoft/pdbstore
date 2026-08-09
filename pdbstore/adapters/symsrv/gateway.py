"""Symbol store gateway speaking the SymSrv format.

This is the single place where the on-store format is turned into bytes: the
``000Admin`` bookkeeping, the ``server.txt`` and ``history.txt`` listings, the
``lastid.txt`` counter and the ``name/signature/name`` layout of the symbols
themselves. Because it is written once on top of a
:class:`BlobStore <pdbstore.usecases.gateways.blob_store.BlobStore>`, every
backend produces a byte-identical store, and a store written to an object
store stays readable by ``symsrv.dll`` and Visual Studio.
"""

import os
import tempfile
from pathlib import Path

from pdbstore import const, exceptions
from pdbstore.adapters.symsrv.compression import Compressor
from pdbstore.entities import symsrv_layout
from pdbstore.entities.entry import TransactionEntry
from pdbstore.entities.transaction import Transaction
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import BinaryIO, Dict, List, Optional, PathLike, Sequence
from pdbstore.usecases.gateways.blob_store import BlobStat, BlobStore
from pdbstore.usecases.gateways.symbol_store import SymbolStoreGateway

__all__ = ["SymSrvGateway"]


class SymSrvGateway(SymbolStoreGateway):
    """Persist a symbol store in the SymSrv format over any blob store."""

    def __init__(self, blob: BlobStore, compressor: Compressor):
        super().__init__()
        self.blob: BlobStore = blob
        self.compressor: Compressor = compressor
        self._next_transaction_id: Optional[str] = None

    @property
    def location(self) -> str:
        """Describe where this store keeps its data.

        :return: The location reported by the underlying blob store.
        """
        return self.blob.location

    def display_path(self, key: str) -> str:
        """Render a key the way an end user expects to see it.

        :param key: The key to be rendered.
        :return: The local path when the backend has one, else the key
            qualified by the store location.
        """
        local = self.blob.local_path(key)
        if local is not None:
            return str(local)
        return f"{self.blob.location}/{key}"

    def prepare(self) -> None:
        """Create the store structure before writing to it.

        :raise:
            :UnexpectedError: The store structure cannot be created.
        """
        try:
            self.blob.make_container("")
            self.blob.make_container(symsrv_layout.admin_key())
        except Exception as exc:
            raise exceptions.UnexpectedError("failed to create symbol store directories") from exc

    def _ensure_admin_dir(self) -> None:
        """Create the administration directory when missing."""
        self.blob.make_container(symsrv_layout.admin_key())

    #
    # Transaction identifiers
    #

    @property
    def next_transaction_id(self) -> str:
        """Peek at the identifier the next transaction will receive.

        :return: The next transaction id, formatted over 10 digits.
        :raise:
            :ReadFileError: The last identifier cannot be read.
            :UnexpectedError: The last identifier is not a number.
        """
        if self._next_transaction_id is None:
            last_id = 0
            key = symsrv_layout.lastid_key()
            if self.blob.exists(key):
                try:
                    last_id = int(self.blob.read_bytes(key).decode("utf-8"))
                except exceptions.ReadFileError:
                    raise
                except Exception as exc:  # pragma: no cover
                    raise exceptions.UnexpectedError(
                        "Failed to extract last id from lastid file"
                    ) from exc

            next_id = last_id + 1
            self._next_transaction_id = f"{next_id:010}"

            PDBStoreOutput().debug(f"{const.LASTID_FILENAME} reported id {next_id}")
            PDBStoreOutput().debug(f"Final id is {self._next_transaction_id}")

        return self._next_transaction_id

    def commit_transaction_id(self, transaction_id: str) -> None:
        """Record an identifier as the last one allocated.

        :param transaction_id: The transaction id that was just used.
        :raise:
            :WriteFileError: The store bookkeeping cannot be updated.
            :UnexpectedError: The identifier is empty.
        """
        if not transaction_id:
            raise exceptions.UnexpectedError("Invalid transaction ID")

        lastid = symsrv_layout.lastid_key()
        try:
            self.blob.write_bytes(lastid, transaction_id.encode("utf-8"))
            # Reset last id
            self._next_transaction_id = None
        except Exception as exc:
            PDBStoreOutput().error("failed to update lastid file")
            PDBStoreOutput().debug(f"with the following error: {str(exc)}")
            raise exceptions.WriteFileError(self.display_path(lastid)) from exc

        pingme = symsrv_layout.pingme_key()
        try:
            self.blob.write_bytes(pingme, b"")
        except Exception as exc:
            PDBStoreOutput().error("failed to touch pingme file")
            raise exceptions.WriteFileError(self.display_path(pingme)) from exc

    #
    # Transaction listings
    #

    def load_transactions(self) -> Dict[str, Transaction]:
        """Load every active transaction, indexed by identifier.

        :return: The transactions listed by ``server.txt``, in file order.
        :raise:
            :ReadFileError: The listing cannot be read.
        """
        key = symsrv_layout.server_key()
        if not self.blob.is_blob(key):
            PDBStoreOutput().verbose(f"{self.display_path(key)} not found")
            return {}

        transactions: Dict[str, Transaction] = {}
        for line in self._read_lines(key):
            transaction = Transaction.parse_line(line, self)
            if transaction and transaction.id:
                transactions[transaction.id] = transaction
        return transactions

    def load_history(self) -> List[Transaction]:
        """Load the full history, including delete operations.

        :return: The transactions listed by ``history.txt``, in file order.
        :raise:
            :ReadFileError: The history cannot be read.
        """
        key = symsrv_layout.history_key()
        if not self.blob.is_blob(key):
            PDBStoreOutput().debug(f"{self.display_path(key)} not found")
            return []

        transactions: List[Transaction] = []
        for line in self._read_lines(key):
            transaction = Transaction.parse_line(line, self)
            if transaction:
                transactions.append(transaction)
        return transactions

    def append_transaction(self, transaction: Transaction) -> None:
        """Add a transaction to the active listing.

        :param transaction: The transaction to be listed.
        :raise:
            :WriteFileError: The listing cannot be updated.
        """
        try:
            self.blob.append_bytes(
                symsrv_layout.server_key(),
                f"{transaction}{os.linesep}".encode("utf-8"),
            )
        except Exception as exc:
            raise exceptions.WriteFileError(
                None, f"failed to append '{transaction}' in server file"
            ) from exc

    def rewrite_transactions(self, transactions: Sequence[Transaction]) -> None:
        """Replace the active listing with the given transactions.

        :param transactions: The transactions that remain active.
        :raise:
            :WriteFileError: The listing cannot be rewritten.
        """
        try:
            self._ensure_admin_dir()
            payload = b"".join(
                f"{transaction}{os.linesep}".encode("utf-8")
                for transaction in sorted(transactions, key=lambda item: item.id)
            )
            self.blob.write_bytes(symsrv_layout.server_key(), payload)
        except Exception as exc:
            raise exceptions.WriteFileError(None, "failed to rewrite the server file") from exc

    def append_history(self, line: str) -> None:
        """Add one raw line to the history.

        The SymSrv history is a plain text file, so a separator has to be
        inserted whenever the previous append did not leave one behind.

        :param line: The line to be recorded.
        :raise:
            :WriteFileError: The history cannot be updated.
        """
        key = symsrv_layout.history_key()
        try:
            stat = self.blob.stat(key)
            if stat is None or stat.size == 0:
                self._ensure_admin_dir()
                payload = b""
            else:
                separator = os.linesep.encode("utf-8")
                tail = self.blob.read_tail(key, len(separator))
                payload = b"" if tail == separator else separator
            self.blob.append_bytes(key, payload + line.encode("utf-8"))
        except OSError as exc:
            raise exceptions.WriteFileError(self.display_path(key)) from exc

    #
    # Transaction entries
    #

    def write_entries(self, transaction: Transaction) -> None:
        """Record the entries referenced by a committed transaction.

        :param transaction: The transaction whose entries must be recorded.
        :raise:
            :WriteFileError: The entries cannot be recorded.
        """
        key = symsrv_layout.transaction_key(transaction.transaction_id)
        try:
            payload = b"".join(
                f"{entry}{os.linesep}".encode("utf-8") for entry in transaction.entries
            )
            self.blob.append_bytes(key, payload)
        except OSError as exc:  # pragma: no cover
            raise exceptions.WriteFileError(self.display_path(key)) from exc

    def load_entries(self, transaction: Transaction) -> List[TransactionEntry]:
        """Load the entries referenced by a transaction.

        :param transaction: The transaction to be resolved.
        :return: The referenced entries.
        :raise:
            :ReadFileError: The entries cannot be read.
        """
        if not transaction.is_committed():
            return []

        key = symsrv_layout.transaction_key(transaction.transaction_id)
        if not self.blob.exists(key):
            return []

        entries: List[TransactionEntry] = []
        try:
            for line in self._read_lines(key):
                entry = TransactionEntry.parse_line(line)
                if entry is None:
                    continue
                entry.compressed = self.blob.is_blob(
                    symsrv_layout.entry_key(entry.file_name, entry.file_hash, True)
                )
                entries.append(entry)
        except Exception as exc:  # pragma: no cover
            raise exceptions.ReadFileError(self.display_path(key)) from exc
        return entries

    def is_deleted(self, transaction: Transaction) -> bool:
        """Determine whether a transaction has been marked as deleted.

        :param transaction: The transaction to be inspected.
        :return: True when the transaction is deleted, else False.
        """
        return self.blob.exists(symsrv_layout.deleted_marker_key(transaction.transaction_id))

    def is_promoted(self, transaction: Transaction) -> bool:
        """Determine whether a transaction has been marked as promoted.

        :param transaction: The transaction to be inspected.
        :return: True when the transaction is promoted, else False.
        """
        return self.blob.exists(symsrv_layout.promoted_marker_key(transaction.transaction_id))

    def mark_deleted(self, transaction: Transaction) -> None:
        """Mark a transaction as deleted.

        :param transaction: The transaction to be marked.
        :raise:
            :RenameFileError: The transaction cannot be marked.
        """
        src = symsrv_layout.transaction_key(transaction.transaction_id)
        if not self.blob.is_blob(src):
            PDBStoreOutput().warning(
                f"{self.display_path(src)} : file not found, "
                "so not possible to mark it as deleted",
            )
            return
        self.blob.move(src, symsrv_layout.deleted_marker_key(transaction.transaction_id))

    def mark_promoted(self, transaction: Transaction) -> None:
        """Mark a transaction as promoted.

        :param transaction: The transaction to be marked.
        :raise:
            :RenameFileError: The transaction cannot be marked.
        """
        src = symsrv_layout.transaction_key(transaction.transaction_id)
        if not self.blob.is_blob(src):
            PDBStoreOutput().warning(
                f"{self.display_path(src)} : file not found, "
                "so not possible to mark it as promoted",
            )
            return
        self.blob.copy(src, symsrv_layout.promoted_marker_key(transaction.transaction_id))

    #
    # Entry content
    #

    def entry_exists(self, entry: TransactionEntry) -> bool:
        """Determine whether an entry is already stored.

        :param entry: The entry to be checked.
        :return: True when the entry content is present, else False.
        """
        return self.blob.is_blob(entry.stored_key)

    def entry_stat(self, entry: TransactionEntry) -> Optional[BlobStat]:
        """Retrieve the metadata of a stored entry.

        :param entry: The entry to be inspected.
        :return: The metadata if the entry is stored, else None.
        """
        return self.blob.stat(entry.stored_key)

    def is_entry_compressed(self, file_name: str, file_hash: str) -> bool:
        """Determine whether a symbol is held compressed in this store.

        :param file_name: The original file name.
        :param file_hash: The file signature.
        :return: True when a cab archive is stored, else False.
        """
        return self.blob.is_blob(symsrv_layout.entry_key(file_name, file_hash, True))

    def store_entry(
        self,
        entry: TransactionEntry,
        force: Optional[bool] = False,
        source: Optional[SymbolStoreGateway] = None,
        skip_if_exists: Optional[bool] = False,
    ) -> bool:
        """Store the content of an entry.

        :param entry: The entry to be stored.
        :param force: True to overwrite an already stored file, else False.
        :param source: Optional store to take the content from.
        :param skip_if_exists: True to report an already stored entry as
            skipped instead of successful.
        :return: True when the entry counts as stored, else False.
        :raise:
            :CabCompressionError: The entry cannot be compressed.
            :CopyFileError: The entry content cannot be stored.
        """
        if self.entry_exists(entry):
            # The file is already present, so keep it as it is
            if skip_if_exists:
                return False
            if not force:
                return True

        self.blob.make_container(entry.dir_key)

        if source is not None:
            return self._promote_entry(entry, source)

        if entry.compressed and entry.exceeds_compression_limit(
            self.compressor.source_size(entry.source_file)
        ):
            # Cab archives top out at 2GB as per Microsoft documentation.
            entry.compressed = False
            PDBStoreOutput().warning(
                f"Disable compression for {entry.source_file} since file size is more than 2GB"
            )

        if entry.compressed:
            self._store_compressed(entry)
        else:
            PDBStoreOutput().debug(
                f"Copying {entry.source_file} to {self.display_path(entry.stored_key)}",
            )
            self.blob.put_file(entry.source_file, entry.stored_key)

        return True

    def extract_entry(self, entry: TransactionEntry, dest_dir: PathLike) -> Optional[PathLike]:
        """Extract a stored entry into a local directory.

        :param entry: The entry to be extracted.
        :param dest_dir: Path to the destination directory.
        :return: Path to the extracted file if successful, else None.
        :raise:
            :DecompressionNotSupportedError: Decompression is unavailable.
            :CabCompressionError: The entry cannot be decompressed.
            :CopyFileError: The entry cannot be copied out.
        """
        if entry.compressed:
            if not self.compressor.is_decompression_supported():
                raise exceptions.DecompressionNotSupportedError()
            PDBStoreOutput().debug(f"Decompressing {entry.stored_name} into {dest_dir}")
            with self._as_local_file(entry.stored_key) as archive:
                self.compressor.decompress(archive, dest_dir)
        else:
            PDBStoreOutput().debug(f"Copying {entry.file_name} into {dest_dir}")
            self.blob.get_file(entry.stored_key, os.path.join(os.fspath(dest_dir), entry.file_name))

        return os.path.join(dest_dir, entry.file_name)

    def has_entry_content(self, entry_dir_key: str) -> bool:
        """Determine whether anything is stored for one entry.

        :param entry_dir_key: The key of the entry directory.
        :return: True when content is stored under that key, else False.
        """
        return self.blob.exists(entry_dir_key)

    def delete_entry_content(self, entry_dir_key: str) -> bool:
        """Remove the stored content of one entry.

        :param entry_dir_key: The key of the entry directory.
        :return: True when something was removed, else False.
        """
        if not self.blob.exists(entry_dir_key):
            return False
        self.blob.delete_prefix(entry_dir_key)
        return True

    def reset(self) -> None:
        """Drop everything cached in memory."""
        self._next_transaction_id = None

    #
    # Internals
    #

    def _promote_entry(self, entry: TransactionEntry, source: SymbolStoreGateway) -> bool:
        """Carry an already stored file over from another store."""
        source_key = symsrv_layout.entry_key(entry.file_name, entry.file_hash, entry.compressed)
        PDBStoreOutput().debug(
            f"Promoting {self.display_path(entry.stored_key)} from "
            f"{source.display_path(source_key)}",
        )
        try:
            stream = source.open_entry(source_key)
            try:
                self.blob.write_stream(entry.stored_key, stream)
            finally:
                stream.close()
        except exceptions.PDBStoreException:
            raise
        except Exception as exc:  # pragma: no cover
            raise exceptions.CopyFileError(source_key, entry.stored_key) from exc
        return True

    def open_entry(self, stored_key: str) -> BinaryIO:
        """Open the content of a stored entry for streamed reading.

        :param stored_key: The key of the stored entry.
        :return: A binary stream over the stored content.
        :raise:
            :ReadFileError: The entry cannot be read.
        """
        return self.blob.open_stream(stored_key)

    def _store_compressed(self, entry: TransactionEntry) -> None:
        """Compress a source file and store the resulting cab archive."""
        if not self.compressor.is_compression_supported():  # pragma: no cover
            raise exceptions.CompressionNotSupportedError()

        target = self.blob.local_path(entry.stored_key)
        if target is not None:
            # The backend keeps its blobs on a filesystem, so the compressor can
            # write the archive straight where it belongs.
            PDBStoreOutput().debug(f"Compressing {entry.source_file} to {target}")
            self.compressor.compress(entry.source_file, target)
            return

        with tempfile.TemporaryDirectory(
            dir=os.environ.get(const.ENV_PDBSTORE_TEMP_DIR) or None
        ) as tmpdir:
            archive = Path(tmpdir) / entry.stored_name
            PDBStoreOutput().debug(
                f"Compressing {entry.source_file} to {self.display_path(entry.stored_key)}"
            )
            self.compressor.compress(entry.source_file, archive)
            self.blob.put_file(archive, entry.stored_key)

    def _as_local_file(self, key: str) -> "_LocalCopy":
        """Expose a blob as a local file, downloading it only when needed."""
        return _LocalCopy(self.blob, key)

    def _read_lines(self, key: str) -> List[str]:
        """Read a text blob and split it into lines."""
        return self.blob.read_bytes(key).decode("utf-8").split("\n")


class _LocalCopy:
    """Context manager exposing a blob as a path on the local filesystem.

    External tools such as the cab compressor take file paths, not streams. A
    filesystem backend already has a path to offer; any other backend gets a
    temporary copy that is removed on exit.
    """

    def __init__(self, blob: BlobStore, key: str):
        self._blob = blob
        self._key = key
        self._tmpdir: Optional[tempfile.TemporaryDirectory] = None  # type: ignore[type-arg]

    def __enter__(self) -> Path:
        local = self._blob.local_path(self._key)
        if local is not None:
            return local
        self._tmpdir = tempfile.TemporaryDirectory(
            dir=os.environ.get(const.ENV_PDBSTORE_TEMP_DIR) or None
        )
        target = Path(self._tmpdir.name) / symsrv_layout.split_key(self._key)[-1]
        self._blob.get_file(self._key, target)
        return target

    def __exit__(self, *args: object) -> None:
        if self._tmpdir is not None:
            self._tmpdir.cleanup()
            self._tmpdir = None

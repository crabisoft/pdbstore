""" Manage a single transaction.
"""
import concurrent.futures as cf
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from pdbstore import io
from pdbstore.exceptions import (
    PDBStoreException,
    ReadFileError,
    RenameFileError,
    WriteFileError,
)
from pdbstore.io.output import PDBStoreOutput
from pdbstore.store.entry import TransactionEntry
from pdbstore.store.summary import OpStatus, Summary
from pdbstore.store.transaction_type import TransactionType
from pdbstore.typing import List, Optional, PathLike, Tuple, Union

__all__ = ["Transaction"]


class TransactionRegEx:
    """Constant related to transaction decryption"""

    # pylint: disable=too-few-public-methods
    TRANSACTION_PREFIX_RE = re.compile(r"(?P<id>\d+),(?P<type>add|del),(?P<tail>.*)")

    TRANSACTION_ADD_RE = re.compile(
        # pylint: disable=line-too-long
        r'(?P<ref>file|ptr),(?P<timestamp>(?:\d\d/\d\d/\d\d\d\d),(?:\d\d:\d\d:\d\d)),"(?P<product>[^"]*)","(?P<version>[^"]*)","(?P<comment>[^"]*)",.*'
    )

    TRANSACTION_DEL_RE = re.compile(r"(?P<id>\d+)")


class Transaction:
    """A SymbolStore transaction representation"""

    def __init__(
        self,
        store: "Store",  # type: ignore[name-defined] # noqa: F821
        transaction_id: Union[str, None] = None,
        transaction_type: TransactionType = TransactionType.ADD,
        ref: str = "file",
        timestamp: Union[datetime, None] = None,
        product: Union[str, None] = None,
        version: Union[str, None] = None,
        comment: Union[str, None] = None,
        deleted_id: Union[str, None] = None,
    ):
        self.store: "Store" = store  # type: ignore[name-defined]  # noqa: F821
        self.transactions_entries: List[TransactionEntry] = []
        self.transaction_id: str = transaction_id  # type: ignore[assignment]
        self.ref: str = ref
        self.timestamp: Union[datetime, None] = timestamp
        self.product: Union[str, None] = product
        self.version: Union[str, None] = version
        self.comment: Union[str, None] = comment
        self.deleted_id: Union[str, None] = deleted_id
        if isinstance(transaction_type, TransactionType):
            self.transaction_type: TransactionType = transaction_type
        elif transaction_type in [member.value for member in TransactionType]:
            self.transaction_type: TransactionType = TransactionType(  # type: ignore[no-redef]
                transaction_type
            )
        else:
            raise PDBStoreException(f"{transaction_type} : unsupported transaction type keyword")

    @property
    def id(self) -> str:  # pylint: disable=invalid-name
        """Retrieve transaction id

        :return: The transcaction id as a string formated using ``%010d`` format
        """
        return self.transaction_id

    def is_committed(self) -> bool:
        """Determine whether the transaction is committed or not

        :return: True if committed (as part of symbol store), else False
        """
        return self.transaction_id is not None

    def is_delete_operation(self) -> bool:
        """Determine whether the transaction is associated to a del operation.

        :return: True if it is a deleted transaction, else False."""
        return self.transaction_type == TransactionType.DEL

    def is_deleted(self) -> bool:
        """Determine whether the transaction is deleted or not

        :return: True if it is a deleted transaction, else False."""
        if self.is_delete_operation():
            return True
        if not self.is_committed():
            return False
        deleted_path: Path = Path(f"{self._entries_file_path()}.deleted")
        if deleted_path.exists():
            return True
        return False

    def is_promoted(self) -> bool:
        """Determine whether the transaction is promoted or not

        :return: True if it is a promoted transaction, else False."""
        if not self.is_committed():
            return False
        promoted_path: Path = Path(f"{self._entries_file_path()}.promoted")
        if promoted_path.exists():
            return True
        return False

    def _entries_file_path(self) -> Path:
        file_path: Path = self.store.admin_dir / self.transaction_id
        return file_path

    def _load_entries(self) -> List[TransactionEntry]:
        """Load and parse transaction file

        :raise:
            :ReadFileError: Failed to read transaction entry file file
        """
        if not self.is_committed():
            return []

        file_path: Path = self._entries_file_path()
        if not file_path.exists():
            return []

        entries = []
        try:
            for line in io.file.read_text_file(file_path, True):
                entry = [s.strip('"') for s in line.strip().split(",")]
                if not entry or not entry[0]:
                    continue
                (file_name, file_hash) = entry[0].split("\\")

                transaction_entry = TransactionEntry.load(
                    self.store, file_name, file_hash, entry[1]
                )

                entries.append(transaction_entry)
        except Exception as exc:  # pragma: no cover
            raise ReadFileError(self._entries_file_path()) from exc
        return entries

    def register_entry(self, pathname: PathLike, compress: bool = False) -> bool:
        """Register a new transaction entry

        This function will ceate a new TransactionEntry before to call add_entry.

        :param pathname: Path to the file
        :param compress: True to compress it, else False
        :return: True if successful, else False
        :raise:
            :FileNotExistsError: The specified file doesn't exists
        """
        hash_value = io.file.compute_hash_key(pathname)
        if not hash_value:
            return False

        new_entry = TransactionEntry(
            self.store,
            os.path.basename(os.fspath(pathname)),
            hash_value,
            pathname,
            compress,
        )
        self.add_entry(new_entry)
        return True

    @property
    def entries(self) -> List[TransactionEntry]:
        """Retrieve the list of associated entries

        :return: List of associated
            :class:`TransactionEntry <pdbstore.store.entry.TransactionEntry>` objects
        """
        if not self.transactions_entries and not self.is_deleted():
            self.transactions_entries = self._load_entries()

        return self.transactions_entries

    @property
    def count(self) -> int:
        """Retrieve the total number of entries

        :return: The total number of registered entries
        """
        return len(self.entries)

    def add_entry(self, entry: TransactionEntry) -> None:
        """Add a new TransactionEntry object

        :param entry: The TransactionEntry object to be added
        """
        self.transactions_entries.append(entry)

    def find_entry(self, file_name: str, file_hash: str) -> Optional[TransactionEntry]:
        """Search a transaction entry given by file name and hash value.

        :param file_name: The file name to be found
        :param file_hash: The required file hash associated to `file_name`
        :return: The requested :class:`TransactionEntry <pdbstore.store.entry.TransactionEntry>`
            object if successful, else None
        """
        for entry in self.entries:
            if entry.file_name == file_name and entry.file_hash == file_hash:
                return entry
        # Not found
        return None

    @staticmethod
    def __commit_entry(
        entry: TransactionEntry,
        force: Optional[bool] = False,
        store: Optional["Store"] = None,  # type: ignore[name-defined] # noqa F821
    ) -> Tuple[TransactionEntry, Union[OpStatus, PDBStoreException]]:
        try:
            return (
                entry,
                OpStatus.SUCCESS if entry.commit(force, store) else OpStatus.SKIPPED,
            )
        except PDBStoreException as exc:  # pragma: no cover
            return (entry, exc)

    def commit(
        self,
        transaction_id: str,
        timestamp: datetime,
        force: Optional[bool] = False,
        store: Optional["Store"] = None,  # type: ignore[name-defined] # noqa F821
    ) -> Summary:
        """Save the transaction on the disk.

        If ``store`` is `None`, this function will consider as a standard transaction,
        else this function will promote the files referenced by this :class:`Transaction` object
        and stored in ``store`` as a new transaction from its associated
        :class:`Store <pdbstore.store.store.Store>` object.

        :param transaction_id: The transaction ID
        :param timestamp: The transaction date/time
        :param store: Optional :class:`Store <pdbstore.store.store.Store>` object
        :param force: True to overwrite any existing file from the store, else False.
        :return: True if successful, else False
        :raise:
            :WriteFileError: Failed to update history file
        """
        summary = Summary(transaction_id, OpStatus.SKIPPED, TransactionType.ADD)

        if self.is_committed():
            PDBStoreOutput().warning(
                f"Transction ID {self.transaction_id} is already committed, so ignore it",
            )
            summary.status = OpStatus.SKIPPED
            return summary
        if not self.transactions_entries:
            PDBStoreOutput().warning("no entry defined, so not possible to commit on the disk")
            summary.status = OpStatus.SKIPPED
            return summary

        self.store.check_admin_dir()

        self.timestamp = timestamp
        self.transaction_id = transaction_id

        # publish all entries files to the store
        with cf.ThreadPoolExecutor() as executor:
            for result in executor.map(
                lambda entry: Transaction.__commit_entry(entry, force, store),
                self.entries,
            ):
                if isinstance(result[1], OpStatus):
                    summary.add_entry(
                        result[0],
                        result[1],
                        TransactionType.ADD,
                    )
                    if summary.status == OpStatus.SKIPPED:
                        summary.status = OpStatus.SUCCESS
                else:
                    summary.status = OpStatus.FAILED
                    summary.add_entry(
                        result[0],
                        OpStatus.FAILED,
                        TransactionType.ADD,
                    )
                    PDBStoreOutput().error(result[1])

        # write new transaction file
        if summary.success(True) > 0:
            try:
                with open(self._entries_file_path(), "ab") as fpe:
                    for entry in self.entries:
                        fpe.write(f"{entry}{os.linesep}".encode("utf-8"))
            except OSError as exo:  # pragma: no cover
                raise WriteFileError(self._entries_file_path()) from exo
        return summary

    def mark_deleted(self) -> None:
        """Tag this transaction as deleted

        This function will rename existing transaction file by appending ``.delete``.

        :raise:
            :RenameFileError: Failed to rename the transaction file
        """
        src: Path = self._entries_file_path()
        if not src.is_file():
            PDBStoreOutput().warning(
                f"{src} : file not found, so not possible to mark it as deleted",
            )
            return
        dest: Path = Path(f"{src}.deleted")
        try:
            os.rename(src, dest)
        except OSError as ex:  # pragma: no cover
            raise RenameFileError(src, dest) from ex

    def mark_promoted(self) -> None:
        """Tag this transaction as promoted

        This function will copy existing transaction file by appending ``.promoted``
        to the new file name.

        :raise:
            :RenameFileError: Failed to rename the transaction file
        """
        src: Path = self._entries_file_path()
        if not src.is_file():
            PDBStoreOutput().warning(
                f"{src} : file not found, so not possible to mark it as promoted",
            )
            return
        dest: Path = Path(f"{src}.promoted")
        try:
            shutil.copyfile(src, dest)
        except IOError as ex:  # pragma: no cover
            raise RenameFileError(src, dest) from ex

    def __str__(self) -> str:
        """Get transaction as a string

        :return: The string representation
        """
        if not self.is_committed():
            return ""

        if self.is_delete_operation():
            if not self.deleted_id:
                return ""
            return f"{self.transaction_id},{self.transaction_type.value},{self.deleted_id}"

        if not self.timestamp:
            return ""
        date_stamp = self.timestamp.strftime("%m/%d/%Y")
        time_stamp = self.timestamp.strftime("%H:%M:%S")

        # pylint: disable=line-too-long
        return f'{self.transaction_id},{self.transaction_type.value},{self.ref},{date_stamp},{time_stamp},"{self.product}","{self.version}","{self.comment}",'

    def __repr__(self) -> str:
        """Get text representation from a Transaction object."""
        return str(self)

    @staticmethod
    def parse_line(store: "Store", line: str) -> Union["Transaction", None]:  # type: ignore[name-defined] # noqa: F821 # pylint: disable=line-too-long
        """Parse a transaction entry from disk.

        Examine ``line`` to extract all information related to an entry and
        create the associated :class:`Transaction` object.

        :param store: The associated :class:`Store <pdbstore.store.store.Store>` object
        :param line: the line to be parsed
        :return: The corresponding Transaction object if successful, else None
        """

        line_res = TransactionRegEx.TRANSACTION_PREFIX_RE.match(line)
        if not line_res:
            return None

        transaction_id = line_res.group("id")
        transaction_type = line_res.group("type")
        if transaction_type == TransactionType.ADD.value:
            add_res = TransactionRegEx.TRANSACTION_ADD_RE.match(line_res.group("tail"))
            if not add_res:
                return None

            timestamp = datetime.strptime(add_res.group("timestamp"), "%m/%d/%Y,%H:%M:%S")
            return Transaction(
                store,
                transaction_id,
                TransactionType.ADD,
                add_res.group("ref"),
                timestamp,
                add_res.group("product"),
                add_res.group("version"),
                add_res.group("comment"),
            )

        del_res = TransactionRegEx.TRANSACTION_DEL_RE.match(line_res.group("tail"))
        if not del_res:
            PDBStoreOutput().debug(f"failed to decompress del type ({line_res.groupdict()})")
            return None

        return Transaction(
            store,
            transaction_id,
            TransactionType.DEL,
            deleted_id=del_res.group("id"),
        )

    def compute_disk_usage(self) -> int:
        """Compute the disk space usage related to all files associated to
        this transaction

        :return: The disk space usage in bytes.
        """
        disk_usage = 0
        for entry in self.entries:
            disk_usage += entry.get_disk_usage()
        return disk_usage

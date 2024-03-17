import datetime
from enum import Enum

from pdbstore import util
from pdbstore.store.entry import TransactionEntry
from pdbstore.store.transaction_type import TransactionType
from pdbstore.typing import Any, Dict, Generator, List, Optional, PathLike, Union

__all__ = ["Summary", "OpStatus"]


class OpStatus(Enum):
    """Lost of predefined operation status."""

    FAILED = "fail"  # Failed operation
    SUCCESS = "success"  # Successful operation
    SKIPPED = "skip"  # Skipped operation

    @staticmethod
    def from_str(label: str) -> "OpStatus":
        """Convert string into OpStatus"""
        if label == OpStatus.FAILED.value:
            return OpStatus.FAILED
        if label == OpStatus.SUCCESS.value:
            return OpStatus.SUCCESS
        return OpStatus.SKIPPED


class Summary:
    """Handle operations summary."""

    def __init__(
        self,
        transaction_id: Optional[str] = None,
        status: "OpStatus" = OpStatus.SUCCESS,
        transaction_type: Optional[TransactionType] = None,
        error_msg: Optional[str] = None,
        references: int = 0,
    ):
        # The associated transaction type
        self._transaction_type: Optional[TransactionType] = transaction_type
        # The associated transaction identifier
        self._transaction_id: Optional[str] = transaction_id
        # Default operation status
        self._status = status
        # Total number of successful operations
        self._success: int = 0
        # Total number of failed operations
        self._failure: int = 0
        # Total number of skipped operations
        self._skip: int = 0
        # Total number of modified references
        self._references: int = references
        # List of files with their operation status
        self._files: List[Dict[str, Any]] = []
        # Custom dictionary of informations
        self._linked: Optional["Summary"] = None
        # Custom error message
        self._error_msg: Optional[str] = error_msg
        if status == OpStatus.FAILED:
            self._failure = 1

    @property
    def transaction_type(self) -> Optional[TransactionType]:
        """Retrieve the associated transaction type."""
        return self._transaction_type

    @property
    def transaction_id(self) -> Optional[str]:
        """Retrieve the associated transaction identifier."""
        return self._transaction_id

    @property
    def status(self) -> OpStatus:
        """Retrieve the operation status."""
        return self._status

    @status.setter
    def status(self, status: OpStatus) -> None:
        """Set the operation status."""
        self._status = status

    def success(self, full: bool = False) -> int:
        """Retrieve the total of successful operations."""
        return self._success + (self._linked.success() if (full and self._linked) else 0)

    def failed(self, full: bool = False) -> int:
        """Retrieve the total of failed operations."""
        return self._failure + (self._linked.failed() if (full and self._linked) else 0)

    def skipped(self, full: bool = False) -> int:
        """Retrieve the total of skipped operations."""
        return self._skip + (self._linked.skipped() if (full and self._linked) else 0)

    def referenced(self, full: bool = False) -> int:
        """Retrieve the total of modified references."""
        return self._references + (self._linked.referenced() if (full and self._linked) else 0)

    def count(self, success_only: bool = False) -> int:
        """Retrieve the total number of Summary object."""
        if not success_only:
            return 1 + (self._linked.count(True) if self._linked else 0)
        cnt = 1 if self.status == OpStatus.SUCCESS else 0
        link = self.linked
        while link:
            if link.status == OpStatus.SUCCESS:
                cnt += 1
            link = link.linked
        return cnt

    @property
    def files(self) -> List[Dict[str, Any]]:
        """Retrieve list of files.

        :return: List of files where each item is a dictionary containing detailed information
            about the associated file.
        """
        return self._files

    @property
    def linked(self) -> Optional["Summary"]:
        """Retrieve the linked summary object.

        :return: The linked :class:`Summary` object if defined, else None.
        """
        return self._linked

    @linked.setter
    def linked(self, linked: "Summary") -> None:
        """Set the linked Summary object."""
        self._linked = linked

    @property
    def error_msg(self) -> Optional[str]:
        """Retrieve custom error message.

        :return: The custom error message.
        """
        return self._error_msg

    def add_file(
        self,
        file_path: PathLike,
        status: OpStatus,
        error_msg: Optional[Union[List[str], str]] = None,
    ) -> Dict[str, Any]:
        """Add new file result given operation status and file path.

        :param file_path: Path to the associated file.
        :param status: Indicate the operation result.
        :param error_msg: Optional error message.
        :return: A dictionary associated to the new added file
        """
        if status == OpStatus.SUCCESS:
            self._success += 1
        elif status == OpStatus.FAILED:
            self._failure += 1
        elif status == OpStatus.SKIPPED:
            self._skip += 1

        self._files.append(
            {
                "path": util.path_to_str(file_path),
                "status": status.value,
                "error": error_msg,
            }
        )
        return self._files[-1]

    def add_entry(
        self,
        entry: TransactionEntry,
        status: OpStatus,
        tr_type: TransactionType,
        error_msg: Optional[Union[List[str], str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Add new file result given operation status and file path.

        :param file_path: Path to the associated file.
        :param status: Indicate the operation result.
        :param tr_type: The transaction type.
        :param error_msg: Optional error message.
        :return: A dictionary associated to the new added entry
        """
        res = self.add_file(
            entry.stored_path.relative_to(entry.store.rootdir),
            status,
            error_msg,
        )
        if status == OpStatus.SUCCESS and tr_type == TransactionType.ADD:
            stat_info = util.str_to_path(entry.file_path).stat()
            res["mtime"] = datetime.datetime.fromtimestamp(
                stat_info.st_mtime,
                datetime.datetime.utcnow().astimezone().tzinfo,
            ).isoformat()
            res["size"] = stat_info.st_size

        for key, val in kwargs.items():
            res[key] = str(val)

        if not self._transaction_type:
            self._transaction_type = tr_type
        return res

    def iterator(self) -> Generator["Summary", "Summary", None]:
        """Iterate over all :class:`Summary object <Summary>` linked nodes"""
        iterator: Optional[Summary] = self
        while iterator:
            yield iterator
            iterator = iterator.linked

import os
import shutil
from pathlib import Path

from pdbstore import exceptions, io, util
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import Optional, PathLike

__all__ = ["TransactionEntry"]


class TransactionEntry:
    """A SymbolStore transaction entry representation"""

    # File size limit to disable compression
    MAX_COMPRESSED_FILE_SIZE: int = 2147482624

    def __init__(
        self,
        store: "Store",  # type: ignore[name-defined] # noqa: F821
        file_name: str,
        file_hash: str,
        source_file: PathLike,
        compressed: bool = False,
    ):
        # The associated symbol store object
        self.store: "Store" = store  # type: ignore[name-defined] # noqa: F821
        # The associated file name
        self.file_name: str = file_name
        # The associated file hash
        self.file_hash: str = file_hash
        # Full path name to the input source file to be stored
        self.source_file: Path = util.str_to_path(source_file)
        # Flag indicating if the stored file is compressed or not
        self.compressed: bool = compressed

    def _stored_dir(self) -> Path:
        """Retrieve the full path of the associated directory from associated store.

        :return: Full path name of the associated directory
        """
        sym_dir: Path = self.store.rootdir / self.file_name / self.file_hash
        return sym_dir

    @property
    def file_path(self) -> Path:
        """Retrieve the original file path.

        :return: The original file path
        """
        return self.source_file

    @property
    def rel_path(self) -> Path:
        """Retrieve the relative path to the stored file

        :return: Relative path name to the stored file
        """
        if not self.compressed:
            return Path(self.file_name, self.file_hash, self.file_name)
        return Path(self.file_name, self.file_hash, (str(self.file_name)[:-1] + "_"))

    @property
    def stored_path(self) -> Path:
        """Retrieve the full path to the stored file

        :return: Full path name to the stored file
        """
        if not self.compressed:
            return self._stored_dir() / self.file_name
        return self._stored_dir() / (str(self.file_name)[:-1] + "_")

    def is_committed(self) -> bool:
        """Determine if this entry has been commit on the disk or not

        :return: True if this entry is valid/published, else False
        """
        file_path = self.stored_path
        return file_path.is_file()

    def is_compressed(self) -> bool:
        """Determine if compression activated or not

        :return: True if compression is enabled, else False
        """
        return self.compressed

    def commit(
        self,
        force: Optional[bool] = False,
        store: Optional["Store"] = None,  # type: ignore[name-defined] # noqa F821
    ) -> bool:
        """Commit transaction entry by storing the required filse into the symbol store.

        If ``store`` is `None`, this function will consider as a standard transaction entry,
        else this function will promote the files referenced by this
        :class:`TransactionEntry <TransactionEntry>` object  and stored them in ``store``
        as a new entry.

        :param force: True to overwrite any existing file from the store, else False.
        :param store: Optional :class:`Store <pdbstore.store.store.Store>` object.

        :return: True if the file is stored successfully, else False if the file was
                 alredy present.
        :raise:
            :CabCompressionError: if an error occurs during compressed file operation
            :CopyFileError: if an error occurs during file storage without compression
        """
        if not force and self.is_committed():
            # The file is already present, so keep it as it is
            return False

        dest_dir = self._stored_dir()

        # Create any missing intermediate directories
        if not dest_dir.is_dir():
            dest_dir.mkdir(parents=True)

        if store is not None:
            # Promote files from another store
            stored_path = store.rootdir / self.file_name / self.file_hash / self.rel_path.name
            PDBStoreOutput().debug(
                f"Promoting {self.stored_path} from {stored_path}",
            )
            try:
                shutil.copy(stored_path, dest_dir)
            except Exception as exc:  # pragma: no cover
                raise exceptions.CopyFileError(stored_path, dest_dir) from exc

            return True

        if self.compressed:
            # Sanity check to limit compression for file having size with less than 2GB
            # 2GB is the limit of cab files as per Microsoft documentation
            if self.MAX_COMPRESSED_FILE_SIZE < io.file.get_file_size(self.source_file):
                self.compressed = False
                PDBStoreOutput().warning(
                    f"Disable compression for {self.source_file} since file size is more than 2GB"
                )

        if self.compressed:
            PDBStoreOutput().debug(
                f"Compressing {self.source_file} to {str(dest_dir / (self.file_name[:-1] + '_'))}"
            )
            io.cab.compress(
                self.source_file, dest_dir / (self.file_name[:-1] + "_")
            )  # type: ignore[misc]
        else:
            PDBStoreOutput().debug(
                f"Copying {self.source_file} to {str(dest_dir / self.file_name)}",
            )
            try:
                shutil.copy(self.source_file, dest_dir)
            except Exception as exc:  # pragma: no cover
                raise exceptions.CopyFileError(self.source_file, dest_dir) from exc

        return True

    def extract(self, dest_dir: PathLike) -> Optional[PathLike]:
        """Extract file from store to specific directory.

        :param dest_dir: Path to output directory

        :return: Path to the output file if successful, else None
        :raise:
            :DecompressionNotSupportedError: Decompression is not supported
            :CabCompressionError: if an error occurs during compressed file operation
            :CopyFileError: if an error occurs during file storage without compression
        """
        if self.compressed:
            if io.cab.decompress is None:
                raise exceptions.DecompressionNotSupportedError()
            PDBStoreOutput().debug(
                f"Decompressing {str(self.file_name[:-1] + '_')} into {dest_dir}"
            )
            io.cab.decompress(self.stored_path, dest_dir)
        else:
            PDBStoreOutput().debug(f"Copying {str(self.file_name)} into {dest_dir}")
            try:
                shutil.copy(self.stored_path, dest_dir)
            except Exception as exc:
                raise exceptions.CopyFileError(self.source_file, dest_dir) from exc

        return os.path.join(dest_dir, self.file_name)

    def __str__(self) -> str:
        """Get text representation

        :return: String representing this object
        """
        return f'"{self.file_name}\\{self.file_hash}","{self.source_file.absolute()}"'

    @staticmethod
    def load(
        store: "Store",  # type: ignore[name-defined] # noqa F821
        file_name: str,
        file_hash: str,
        source_file: PathLike,
    ) -> "TransactionEntry":
        """Load transaction entry from disk.

        Examine files in symbol store directory and create an transaction
        entry object that represents it.

        :param store: The associated SymbolSymbolStore object
        :param file_name: The file name for the transaction entry
        :param file_hash: The file hash
        :param source_file: Full path to the input source file
        :return: The new :class:`TransactionEntry` object
        """
        compressed_path = store.rootdir / file_name / file_hash / (str(file_name)[:-1] + "_")
        return TransactionEntry(store, file_name, file_hash, source_file, compressed_path.is_file())

    @staticmethod
    def create(
        store: "Store", file_path: PathLike  # type: ignore[name-defined] # noqa: F821
    ) -> Optional["TransactionEntry"]:
        """
        Create a new transaction entry given store and file path

        This function will ceate a new :class:`TransactionEntry` based on input
        information. This function assumes that the file is at least
        present without any compression.

        :param store: The associated Store object
        :param file_path: The file name for the transaction entry
        :return: :class:`TransactionEntry` object if successful, else None on
                 error.
        :raise:
            :FileNotExistsError: The specified file doesn't exists
        """
        file_hash = io.file.compute_hash_key(file_path)
        if not file_hash:
            return None

        file_name = os.path.basename(os.fspath(file_path))
        compressed_path = store.rootdir / file_name / file_hash / (str(file_name)[:-1] + "_")

        new_entry = TransactionEntry(
            store,
            file_name,
            file_hash,
            file_path,
            compressed_path.is_file(),
        )
        return new_entry

    def get_disk_usage(self) -> int:
        """Compute the disk space usage related to this transaction entry

        :return: The disk space usage in bytes.
        """
        disk_usage = 0
        file_path = self.stored_path
        if file_path.is_file():
            try:
                disk_usage = file_path.stat().st_size
            except OSError:  # pragma: no cover
                PDBStoreOutput().error(f"failed to get file size for {str(file_path)}")
        return disk_usage

    def clone(
        self,
        store: Optional["Store"] = None,  # type: ignore[name-defined] # noqa: F821
        promoted: Optional[bool] = False,
    ) -> "TransactionEntry":
        """Clone the transaction entry.

        :param store: Optional :class:`Store <pdbstore.store.store.Store>` object to be
                      associated to the cloned entry
        :return: The cloned :class:`TransactionEntry` object
        """
        return TransactionEntry(
            store,
            self.file_name,
            self.file_hash,
            self.stored_path if promoted else self.source_file,
            False if promoted else self.compressed,
        )

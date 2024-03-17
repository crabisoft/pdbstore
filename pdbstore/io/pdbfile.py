import binascii
import math
import os
import struct

from pdbstore import util
from pdbstore.exceptions import (
    FileNotExistsError,
    ParseFileError,
    PDBInvalidStreamIndexError,
    PDBSignatureNotFoundError,
)
from pdbstore.typing import Any, IO, Optional, PathLike, Tuple, Union

PDB_HEADER_SIGNATURE = b"Microsoft C/C++ MSF 7.00\r\n\x1ADS\0\0\0"
PDB_STREAM_INDEX = 1
DBI_STREAM_INDEX = 3


class RootStream:
    """A Root stream representation.
    This class provides access to api to properly extract all required information
    from PDB stream
    """

    def __init__(self, fps: IO[Any], page_size: int, stream_size: int):
        """Class initialization.

        :param fps: File object to the previously opened file
        :param page_size: The current page size
        :param stream_size: The root stream size
        """
        self.fps: IO[Any] = fps
        self.page_size: int = page_size
        self.stream_size: int = stream_size
        self.streams_count: int = 0

        # Build the list of available streams
        self.page_indexes: Any = self._load_streams()

        # Determine the total number of streams
        self.streams_count = struct.unpack("<I", self._read(0, 4))[0]

    def _round(self, bytes_count: int) -> int:
        """Compute the total number of pages required to store the specified
        number of bytes.

        :param bytes_count: total number of bytes
        :return: The total number of pages
        """
        return int(math.ceil(float(bytes_count) / self.page_size))

    def _load_streams(self) -> Tuple[Any, ...]:
        """Build the list of page index for each available streams"""
        num_pages = self._round(self.stream_size)

        # Move to the beginning of the root stream
        # PDB Version 7 has 5 fields of 4 bytes, so we skip it to be sure
        # that we are on the page number list byte
        self.fps.seek(len(PDB_HEADER_SIGNATURE) + 4 * 5)

        # 4 bytes per page number
        num_root_index_pages = self._round(num_pages * 4)

        # Read the page number list
        # pylint: disable=consider-using-f-string
        page_number_list = struct.unpack(
            "<%sI" % num_root_index_pages,
            self.fps.read(4 * num_root_index_pages),
        )

        page_list_data = b""
        for index in page_number_list:
            self.fps.seek(index * self.page_size)
            page_list_data += self.fps.read(self.page_size)

        page_list_fmt = "<" + (f"{num_pages}I")
        return struct.unpack(page_list_fmt, page_list_data[: num_pages * 4])

    def _seek(self, page_index: int, offset: int) -> None:
        """Move to a specific page.

        :param page_index: the required page zero-based index
        :param offset: the number of bytes to offset from the beginning of the page
        """
        self.fps.seek(self.page_indexes[page_index] * self.page_size + offset)

    def _read(self, start: int, length: int) -> Any:
        """Read bytes given a position and length.

        :param start: the global offset where to read
        :param length: number of bytes to read
        :return: A bytes array
        """
        # Compute page index and offset value
        start_page = start // self.page_size
        start_byte = start % self.page_size

        # Move to the required position
        self._seek(start_page, start_byte)

        # Read the required bytes
        partial_size = min(length, self.page_size - start_byte)
        result = self.fps.read(partial_size)
        length -= partial_size
        while length > 0:
            start_page += 1
            self._seek(start_page, 0)
            partial_size = min(self.page_size, length)
            result += self.fps.read(partial_size)
            length -= partial_size
        return result

    def _get_stream_size(self, stream_index: int) -> int:
        """Get the size in bytes for a specific stream

        :param stream_index: The stream zero-based index
        :return: The stream size in bytes
        :raise:
            :PDBInvalidStreamIndexError: Invalid stream index value
        """
        if stream_index >= self.streams_count:
            raise PDBInvalidStreamIndexError(stream_index)

        # 4 : number of streams
        # 4 * num_streams: size for each stream
        return int(struct.unpack("<I", self._read(stream_index * 4 + 4, 4))[0])

    def _get_stream_page_indexes(self, stream_index: int) -> Any:
        """Get stream-s page indexes given by stream index

        :param stream_index: The stream zero-based index
        :return: Tuple containing page indexes
        :raise:
            :PDBInvalidStreamIndexError: Invalid stream index value
        """
        if stream_index >= self.streams_count:
            raise PDBInvalidStreamIndexError(stream_index)

        # 4 : number of streams
        # 4 * num_streams: size for each stream
        page_offset = 4 + 4 * self.streams_count

        for index in range(stream_index):
            page_offset += self._round(self._get_stream_size(index)) * 4

        num_pages = self._round(self._get_stream_size(stream_index))

        return struct.unpack(f"<{num_pages}I", self._read(page_offset, 4 * num_pages))

    def parse_guid(self) -> str:
        """Extract GUID from PDB stream (stream 1)

        :return: The parsed GUID as a string
        """
        pdb_stream_pages = self._get_stream_page_indexes(PDB_STREAM_INDEX)
        self.fps.seek(pdb_stream_pages[0] * self.page_size + 3 * 4)
        pdb_stream_data = self.fps.read(4 + 2 * 2 + 8)

        # pylint: disable=consider-using-f-string
        guid_data = struct.unpack("<IHH8s", pdb_stream_data)
        return "%.8X%.4X%.4X%s" % (
            guid_data[0],
            guid_data[1],
            guid_data[2],
            binascii.hexlify(guid_data[3]).decode("utf-8").upper(),
        )

    def parse_age(self) -> Union[int, None]:
        """Extract PDB age from DBI stream.

        :return: The PDB file's age as an integer
        """
        dbi_stream_pages = self._get_stream_page_indexes(DBI_STREAM_INDEX)
        if len(dbi_stream_pages) <= 0:
            return None

        self.fps.seek(dbi_stream_pages[0] * self.page_size + 2 * 4)
        dbi_stream_data = self.fps.read(4)

        age: Any = struct.unpack("<I", dbi_stream_data)

        return int(age[0])


class PDB:
    """A Program Database (PDB) representation.
    This class provides access to :

    - PDB file's GUID through ``guid`` data member as a string.
    - PDB file's age through ``age``` data member as an integer.
    """

    _guid: str
    _age: Optional[int]
    _root: Optional[RootStream]

    def __init__(self, file_path: PathLike):
        """Initialize PDB given a file path

        :param file_path: Path to the pdb file
        :raise:
            :FileNotExistsError: the specified file does not exists
            :ParseFileError: if the specified file is not a valid PDB file
            :PDBInvalidStreamIndexError: if invalid pdb file content
        """
        pdb_path = util.str_to_path(file_path)
        if not pdb_path or not pdb_path.is_file():
            raise FileNotExistsError(f"{file_path} : invalid file pdb path")

        with pdb_path.open("rb") as fppdb:
            header = fppdb.read(len(PDB_HEADER_SIGNATURE))
            if header != PDB_HEADER_SIGNATURE:
                raise PDBSignatureNotFoundError(str(file_path))

            try:
                # Parse header to fetch root stream information
                page_size, _, _, root_stream_size = struct.unpack("<IIII", fppdb.read(4 * 4))
                self._root = RootStream(fppdb, page_size, root_stream_size)

                # Extract GUID and age
                self._guid = self._root.parse_guid()
                self._age = self._root.parse_age()
            except Exception as exf:
                raise ParseFileError(file_path) from exf

            if self._age is None and os.path.splitext(pdb_path)[1] in [
                ".bsc",
                ".bsr",
            ]:
                raise ParseFileError(str(file_path))

    @property
    def guid(self) -> str:
        """Retrieve PDB file's GUID

        :return: A string containing the PDB file's GUID.
        """
        return self._guid

    @property
    def age(self) -> Optional[int]:
        """Retrieve PDB file's age.

        :return: A string containing the PDB file's age.
        """
        return self._age

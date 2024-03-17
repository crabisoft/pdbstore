import binascii
import struct

from pdbstore import util
from pdbstore.exceptions import (
    FileNotExistsError,
    ParseFileError,
    PDBSignatureNotFoundError,
)
from pdbstore.typing import Any, IO, List, Optional, PathLike, Tuple

PDB_HEADER_SIGNATURE = b"BSJB"
PDB_STREAM_INDEX = 1
DBI_STREAM_INDEX = 3
STREAM_PDB = "#Pdb"


class StreamHeader:
    """Stream information"""

    def __init__(self, name: str, offset: int, size: int) -> None:
        """Class initialization.

        :param name: The stream name
        :param offset: Offset from beginning of file
        :param size: The stream size
        """
        self._name: str = name
        self._offset: int = offset
        self._size: int = size

    @property
    def name(self) -> str:
        """Retrieve the stream name"""
        return self._name

    @property
    def offset(self) -> int:
        """Retrieve the stream offset"""
        return self._offset

    @property
    def size(self) -> int:
        """Retrieve the stream size"""
        return self._size


class RootStream:
    """A Root stream representation.
    This class provides access to api to properly extract all required information
    from PDB stream
    """

    def __init__(self, fps: IO[Any]):
        """Class initialization.

        :param fps: File object to the previously opened file
        """
        self.fps: IO[Any] = fps
        self.versions: Tuple[int, int] = (0, 0)

        # Build the list of available streams
        self.streams: List[StreamHeader] = self._load_streams()

    def _load_streams(self) -> List[StreamHeader]:
        """Build the list of available streams"""

        self.fps.seek(0)

        # We assume that magic key is already checked
        _, major, minor, _, version_len = struct.unpack("<IHHII", self.fps.read(4 + 2 + 2 + 4 + 4))
        self.versions = (major, minor)
        self.version_name = struct.unpack(f"<{version_len}c", self.fps.read(version_len))
        _, stream_count = struct.unpack("<HH", self.fps.read(2 + 2))
        streams: List[StreamHeader] = []
        for _ in range(0, stream_count):
            offset, size = struct.unpack("<II", self.fps.read(4 + 4))
            chars: Any = []
            while True:
                utf8_ch = struct.unpack("<BBBB", self.fps.read(4))
                if utf8_ch[3] == 0:
                    name = bytes(chars).decode("utf-8")
                    streams.append(StreamHeader(name, offset, size))
                    break
                chars += utf8_ch
        return streams

    def _get_stream_by_name(self, name: str) -> StreamHeader:
        """Retrieve a stream given by its name"""
        return list(filter(lambda s: s.name == name, self.streams))[0]

    def parse_guid(self) -> str:
        """Extract GUID from #Pdb stream

        :return: The parsed GUID as a string
        """
        stream: StreamHeader = self._get_stream_by_name(STREAM_PDB)
        self.fps.seek(stream.offset)

        # pylint: disable=consider-using-f-string
        guid_data = struct.unpack("<IHH8s", self.fps.read(16))
        return "%.8X%.4X%.4X%s" % (
            guid_data[0],
            guid_data[1],
            guid_data[2],
            binascii.hexlify(guid_data[3]).decode("utf-8").upper(),
        )

    def parse_age(self) -> int:
        """Extract PDB age from #Pdb stream.

        The age for Portable PDBs is irrelevant (always 1 in the PE debug directory),
        so always return 1

        :return: The PDB file's age as an integer
        """
        # Original code to use age from stream itself
        # stream: Optional[StreamHeader] = self._get_stream_by_name(STREAM_PDB)
        # self.fps.seek(stream.offset + 16)
        # age: int = struct.unpack("<I", self.fps.read(4))[0]
        age = 1
        return age


class PortablePDB:
    """A Portable Program Database (PDB) representation.
    This class provides access to :

    - PDB file's GUID through ``guid`` data member as a string.
    - PDB file's age through ``age``` data member as an integer.
    """

    _guid: str
    _age: int
    _root: RootStream

    def __init__(self, file_path: PathLike):
        """Initialize PortablePDB given a file path

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
                self._root = RootStream(fppdb)
            except struct.error as exs:
                raise ParseFileError(file_path) from exs
            try:
                # Extract GUID and age
                self._guid = self._root.parse_guid()
                self._age = self._root.parse_age()
            except Exception as exf:
                raise ParseFileError(file_path) from exf

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

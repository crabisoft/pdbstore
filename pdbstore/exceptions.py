from pdbstore.typing import Optional, PathLike, Union


#
# Generic exception
#
class PDBStoreException(Exception):
    """PDBStore based exception object"""

    def __init__(self, message: str) -> None:
        Exception.__init__(self, message)
        self.message = message


#
# Command-line utility exception
#


class PDBAbortExecution(PDBStoreException):
    """Abort but with success the current execution"""

    def __init__(self, exitcode: int = 0) -> None:
        self.exitcode = exitcode
        PDBStoreException.__init__(self, "")


class PDBInvalidCommandNameException(PDBStoreException):
    """Invalid command or action name"""

    def __init__(self, name: Optional[str] = None) -> None:
        if name:
            PDBStoreException.__init__(self, f"Unknown '{name}' command")
        else:
            PDBStoreException.__init__(self, "No command name given")


class PDBInvalidSubCommandNameException(PDBStoreException):
    """Invalid sub-command name"""

    def __init__(self, name: Optional[str] = None) -> None:
        if name:
            PDBStoreException.__init__(self, f"Unknown '{name}' sub-command")
        else:
            PDBStoreException.__init__(self, "No sub-command name given")


class CommandLineError(PDBStoreException):
    """One command-line argument is not defined properly"""

    def __init__(self, message: str) -> None:
        PDBStoreException.__init__(self, message)


class CabCompressionError(PDBStoreException):
    """Failed to compress the requested file"""

    def __init__(self, message: str) -> None:
        PDBStoreException.__init__(self, message)


class CompressionNotSupportedError(PDBStoreException):
    """Compression not support"""

    def __init__(self) -> None:
        PDBStoreException.__init__(self, "CAB compression not supported")


class DecompressionNotSupportedError(PDBStoreException):
    """Decompression not support"""

    def __init__(self) -> None:
        PDBStoreException.__init__(self, "CAB decompression not supported")


class CopyFileError(PDBStoreException):
    """Failed to store the specified file"""

    def __init__(self, pathname: PathLike, dest: PathLike) -> None:
        PDBStoreException.__init__(self, f"failed to copy {pathname} into {dest}")


class UnknowFileTypeError(PDBStoreException):
    """Unknown file type"""

    def __init__(self, pathname: PathLike) -> None:
        PDBStoreException.__init__(self, f"{pathname} : not a known file type")


class InvalidPEFile(PDBStoreException):
    """Not a valid PE file"""

    def __init__(self, pathname: PathLike) -> None:
        PDBStoreException.__init__(self, f"{pathname} : not a valid pe file")


class FileNotExistsError(PDBStoreException):
    """File not found"""

    def __init__(self, pathname: PathLike) -> None:
        PDBStoreException.__init__(self, f"{pathname} : file not found")


class InvalidCommandLineDefinitionError(PDBStoreException):
    """Invalid subcommand definition when parsing command line."""

    def __init__(self) -> None:
        PDBStoreException.__init__(
            self,
            "subcommand attribute not defined from required subcommand parser",
        )


class NotSupportedError(PDBStoreException):
    """Unsupported functionality"""

    def __init__(self, message: str) -> None:
        PDBStoreException.__init__(self, message)


class ParseFileError(PDBStoreException):
    """Unexcepted error when parsing a file"""

    def __init__(self, pathname: PathLike) -> None:
        PDBStoreException.__init__(self, f"failed to parse {pathname}")


class PDBInvalidStreamIndexError(PDBStoreException):
    """Invalid stream index from PDB file"""

    def __init__(self, index: int) -> None:
        PDBStoreException.__init__(self, f"{index} : invalid stream index")


class PDBSignatureNotFoundError(PDBStoreException):
    """Invalid PDB file signature detected"""

    def __init__(self, signature: str) -> None:
        PDBStoreException.__init__(self, f"{signature} : invalid PDB signature")


class ReadFileError(PDBStoreException):
    """Unexcepted error when reading a file"""

    def __init__(self, pathname: PathLike) -> None:
        PDBStoreException.__init__(self, f"failed to read data from {pathname}")


class RenameFileError(PDBStoreException):
    """Failed to rename a file"""

    def __init__(self, src: PathLike, dest: PathLike) -> None:
        PDBStoreException.__init__(self, f"failed to rename {src} into {dest}")


class TransactionException(PDBStoreException):
    """Transaction based exception object"""

    def __init__(self, message: str) -> None:
        PDBStoreException.__init__(self, message)


class TransactionNotFoundError(TransactionException):
    """Specific transaction ID not found"""

    def __init__(self, transaction_id: Union[int, str]) -> None:
        if isinstance(transaction_id, int):
            transaction_id = f"{transaction_id:010}"
        TransactionException.__init__(
            # pylint: disable=line-too-long
            self,
            f"ID {transaction_id} doesn't exist",
        )


class ImproperTransactionTypeError(TransactionException):
    """Specific transaction ID found but with improper type"""

    def __init__(
        self, transaction_id: Union[int, str], transaction_type: str, expected_type: str
    ) -> None:
        TransactionException.__init__(
            # pylint: disable=line-too-long
            self,
            f"ID {transaction_id} exist but {transaction_type} detected and {expected_type} found",
        )


class UnexpectedError(PDBStoreException):
    """Unexpected error"""

    def __init__(self, message: str) -> None:
        PDBStoreException.__init__(self, message)


class WriteFileError(PDBStoreException):
    """Unexpected error occurs when updating a file"""

    def __init__(self, pathname: Union[None, PathLike], msg: Optional[str] = None) -> None:
        if not msg:
            msg = f"failed to write data in {pathname}"
        PDBStoreException.__init__(self, msg)


class HTTPAPIError(PDBStoreException):
    """Base HTTP API Exception"""

    def __init__(self, message: str) -> None:
        PDBStoreException.__init__(self, message)


class HTTPStatusCodeError(HTTPAPIError):
    """Status code Exception"""


#
# Configuration exception
#


class ConfigError(PDBStoreException):
    """Basic configuration file error."""


class ConfigIDError(ConfigError):
    """Invalid store id definition."""


class ConfigDataError(ConfigError):
    """Invalid data configuration definition."""


class ConfigMissingError(ConfigError):
    """Specified configuration file not found."""

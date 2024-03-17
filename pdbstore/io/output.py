import os
import sys
import traceback

from colorama import Fore, Style

from pdbstore import const
from pdbstore.exceptions import PDBStoreException
from pdbstore.io.colors import color_enabled, is_terminal
from pdbstore.typing import Dict, Optional, Union

LEVEL_QUIET = 80  # -q
LEVEL_ERROR = 70  # Errors
LEVEL_WARNING = 60  # Warnings
LEVEL_NOTICE = 50  # Important messages to attract user attention.
LEVEL_STATUS = 40  # Default - The main interesting messages.
LEVEL_VERBOSE = 30  # -V  Detailed informational messages.
LEVEL_DEBUG = 20  # -VV Closely related to internal implementation details
LEVEL_TRACE = 10  # -VVV Fine-grained messages with very low-level implementation details


class Color:  # pylint: disable=too-few-public-methods
    """Wrapper around colorama colors that are undefined in importing"""

    RED = Fore.RED  # @UndefinedVariable
    WHITE = Fore.WHITE  # @UndefinedVariable
    CYAN = Fore.CYAN  # @UndefinedVariable
    GREEN = Fore.GREEN  # @UndefinedVariable
    MAGENTA = Fore.MAGENTA  # @UndefinedVariable
    BLUE = Fore.BLUE  # @UndefinedVariable
    YELLOW = Fore.YELLOW  # @UndefinedVariable
    BLACK = Fore.BLACK  # @UndefinedVariable

    BRIGHT_RED = Style.BRIGHT + Fore.RED  # @UndefinedVariable
    BRIGHT_BLUE = Style.BRIGHT + Fore.BLUE  # @UndefinedVariable
    BRIGHT_YELLOW = Style.BRIGHT + Fore.YELLOW  # @UndefinedVariable
    BRIGHT_GREEN = Style.BRIGHT + Fore.GREEN  # @UndefinedVariable
    BRIGHT_CYAN = Style.BRIGHT + Fore.CYAN  # @UndefinedVariable
    BRIGHT_WHITE = Style.BRIGHT + Fore.WHITE  # @UndefinedVariable
    BRIGHT_MAGENTA = Style.BRIGHT + Fore.MAGENTA  # @UndefinedVariable


if os.getenv(const.ENV_PDBSTORE_COLOR_DARK):
    Color.WHITE = Fore.BLACK
    Color.CYAN = Fore.BLUE
    Color.YELLOW = Fore.MAGENTA
    Color.BRIGHT_WHITE = Fore.BLACK
    Color.BRIGHT_CYAN = Fore.BLUE
    Color.BRIGHT_YELLOW = Fore.MAGENTA
    Color.BRIGHT_GREEN = Fore.GREEN


class PDBStoreOutput:
    """Manage all PDBStore output messages"""

    # Singleton
    _pdbstore_output_level: int = LEVEL_STATUS
    _pdbstore_output_file: Optional[str] = None

    def __init__(self, scope: str = "") -> None:
        self.stream = sys.stderr
        self._scope = scope
        if self._pdbstore_output_file:
            self.stream = open(  # pylint: disable=consider-using-with
                self._pdbstore_output_file, "wt", encoding="utf-8"
            )
        self._color: bool = color_enabled(self.stream)

    @classmethod
    def define_log_level(cls, level_name: Optional[str] = None) -> None:
        """
        Translates the verbosity level entered by a PDBStore command.
        If it's `None` (-V), it will be defaulted to `verbose` level.

        :param level_name: `str` or `None`, where `None` is the same as `verbose`.
        """
        try:
            level = {
                "quiet": LEVEL_QUIET,  # -Vquiet 80
                "error": LEVEL_ERROR,  # -Verror 70
                "warning": LEVEL_WARNING,  # -Vwaring 60
                "notice": LEVEL_NOTICE,  # -Vnotice 50
                "status": LEVEL_STATUS,  # -Vstatus 40
                "info": LEVEL_STATUS,  # -Vstatus 40
                None: LEVEL_VERBOSE,  # -V 30
                "verbose": LEVEL_VERBOSE,  # -Vverbose 30
                "debug": LEVEL_DEBUG,  # -Vdebug 20
                "V": LEVEL_DEBUG,  # -VV 20
                "trace": LEVEL_TRACE,  # -Vtrace 10
                "VV": LEVEL_TRACE,  # -VVV 10
            }[level_name]
        except KeyError:
            # pylint: disable=raise-missing-from
            raise PDBStoreException(f"Invalid argument '-V{level_name}'")

        cls._pdbstore_output_level = level

    @classmethod
    def define_log_output(cls, file_path: Optional[str] = None) -> None:
        """
        Translates the verbosity level entered by a PDBStore command.
        If it's `None` (-V), it will be defaulted to `verbose` level.

        :param file_path: Optional path to output log file.
        """
        cls._pdbstore_output_file = file_path

    @classmethod
    def level_allowed(cls, level: int) -> bool:
        """
        Determines if a level can print associated message or not.
        """
        return cls._pdbstore_output_level <= level

    @classmethod
    def output_level(cls) -> int:
        """Retrieve the current output level.

        Returns:
            int: The current output level
        """
        return cls._pdbstore_output_level

    @property
    def color(self) -> bool:
        """
        Determines if ANSI color is enabled or not.
        """
        return self._color

    @property
    def scope(self) -> str:
        """
        Retrieves the current scope
        """
        return self._scope

    @scope.setter
    def scope(self, out_scope: str) -> None:
        """
        Defines the current scope.
        """
        self._scope = out_scope

    @property
    def is_terminal(self) -> bool:
        """
        Determines if a stream is interactive.
        """
        return is_terminal(self.stream)

    def writeln(
        self, data: str, fore: Optional[str] = None, back: Optional[str] = None
    ) -> "PDBStoreOutput":
        """Writes a line including newline sequence"""
        return self.write(data, fore, back, newline=True)

    def write(
        self,
        data: str,
        fore: Optional[str] = None,
        back: Optional[str] = None,
        newline: bool = False,
    ) -> "PDBStoreOutput":
        """Writes a message."""
        if self._pdbstore_output_level > LEVEL_NOTICE:
            return self
        if self._color and (fore or back):
            data = f"{fore or ''}{back or ''}{data}{Style.RESET_ALL}"

        if newline:
            data = f"{data}\n"
        self.stream.write(data)
        self.stream.flush()
        return self

    def rewrite_line(self, line: str) -> None:
        """Abbreviates a line and display it."""
        tmp_color = self._color
        self._color = False
        total_size = 70
        limit_size = total_size // 2 - 3
        if len(line) > total_size:
            line = line[0:limit_size] + " ... " + line[-limit_size:]
        self.write(f"\r{line}{' ' * (total_size - len(line))}")
        self.stream.flush()
        self._color = tmp_color

    def _write_message(
        self,
        msg: Union[str, Dict[str, str]],
        fore: Optional[str] = None,
        back: Optional[str] = None,
    ) -> None:
        if isinstance(msg, dict):
            # For traces we can receive a dict already, we try to transform then
            # into more natural text
            msg = ", ".join([f"{k}: {v}" for k, v in msg.items()])
            msg = f"=> {msg}"

        ret = ""
        if self._scope:
            if self._color:
                ret = f"{fore or ''}{back or ''}{self.scope}:{Style.RESET_ALL} "
            else:
                ret = f"{self.scope}: "

        if self._color:
            ret += f"{fore or ''}{back or ''}{msg}{Style.RESET_ALL}"
        else:
            ret += f"{msg}"

        self.stream.write(f"{ret}\n")
        self.stream.flush()

    def trace(self, msg: Union[str, Dict[str, str]]) -> "PDBStoreOutput":
        """
        Prints a trace message.
        """
        if self._pdbstore_output_level <= LEVEL_TRACE:
            self._write_message(msg, fore=Color.BRIGHT_WHITE)
        return self

    def debug(self, msg: Union[str, Dict[str, str]]) -> "PDBStoreOutput":
        """
        Prints a debug message.
        """
        if self._pdbstore_output_level <= LEVEL_DEBUG:
            self._write_message(msg)
        return self

    def verbose(
        self,
        msg: Union[str, Dict[str, str]],
        fore: Optional[str] = None,
        back: Optional[str] = None,
    ) -> "PDBStoreOutput":
        """
        Prints a verbose message.
        """
        if self._pdbstore_output_level <= LEVEL_VERBOSE:
            self._write_message(msg, fore=fore, back=back)
        return self

    def info(
        self,
        msg: Union[str, Dict[str, str]],
        fore: Optional[str] = None,
        back: Optional[str] = None,
    ) -> "PDBStoreOutput":
        """
        Prints a status/informative message.
        """
        if self._pdbstore_output_level <= LEVEL_STATUS:
            self._write_message(msg, fore=fore, back=back)
        return self

    def title(self, msg: Union[str, Dict[str, str]]) -> "PDBStoreOutput":
        """
        Prints a title.
        """
        if self._pdbstore_output_level <= LEVEL_NOTICE:
            self._write_message(f"\n======== {msg} ========", fore=Color.BRIGHT_MAGENTA)
        return self

    def subtitle(self, msg: Union[str, Dict[str, str]]) -> "PDBStoreOutput":
        """
        Prints a subtitle.
        """
        if self._pdbstore_output_level <= LEVEL_NOTICE:
            self._write_message(f"\n-------- {msg} --------", fore=Color.BRIGHT_MAGENTA)
        return self

    def highlight(self, msg: Union[str, Dict[str, str]]) -> "PDBStoreOutput":
        """
        Prints a highlighted message.
        """
        if self._pdbstore_output_level <= LEVEL_NOTICE:
            self._write_message(msg, fore=Color.BRIGHT_MAGENTA)
        return self

    def success(self, msg: Union[str, Dict[str, str]]) -> "PDBStoreOutput":
        """
        Prints a success message.
        """
        if self._pdbstore_output_level <= LEVEL_NOTICE:
            self._write_message(msg, fore=Color.BRIGHT_GREEN)
        return self

    def warning(self, msg: Union[str, Dict[str, str]]) -> "PDBStoreOutput":
        """
        Prints a warning message.
        """
        if self._pdbstore_output_level <= LEVEL_WARNING:
            self._write_message(f"WARNING: {msg}", Color.YELLOW)
        return self

    def error(self, msg: Union[BaseException, str, Dict[str, str]]) -> "PDBStoreOutput":
        """
        Prints an error message.
        """
        if self._pdbstore_output_level <= LEVEL_ERROR:
            if isinstance(msg, BaseException):  # pragma: no cover
                lines = traceback.format_exception(type(msg), value=msg, tb=msg.__traceback__)
                exc_msg = ("\n".join(lines)).replace("\n", "\n       ")
                self._write_message(f"ERROR: {exc_msg}", Color.RED)
            else:
                self._write_message(f"ERROR: {msg}", Color.RED)
        return self

    def flush(self) -> None:
        """
        Flush associated stream.
        """
        self.stream.flush()


def cli_out_write(
    data: Union[str, Dict[str, str]],
    fore: Optional[str] = None,
    back: Optional[str] = None,
    endline: str = "\n",
    indentation: int = 0,
) -> None:
    """
    Output to be used by formatters to dump information to stdout
    """
    fore_ = fore or ""
    back_ = back or ""
    if (fore or back) and color_enabled(sys.stdout):
        data = f"{' ' * indentation}{fore_}{back_}{data}{Style.RESET_ALL}{endline}"
    else:
        data = f"{' ' * indentation}{data}{endline}"

    sys.stdout.write(data)

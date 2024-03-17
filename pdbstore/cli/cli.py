import importlib
import os
import pkgutil
import signal
import sys
import textwrap
import traceback
from collections import defaultdict
from difflib import get_close_matches
from inspect import getmembers

from pdbstore import __version__ as pdbstore_version
from pdbstore.cli.command import PDBStoreSubCommand
from pdbstore.cli.exit_codes import (
    ERROR_COMMAND_NAME,
    ERROR_ENCOUNTERED,
    ERROR_GENERAL,
    ERROR_INVALID_CONFIGURATION,
    ERROR_SIGTERM,
    ERROR_SUBCOMMAND_NAME,
    ERROR_UNEXPECTED,
    SUCCESS,
    USER_CTRL_BREAK,
    USER_CTRL_C,
)
from pdbstore.exceptions import (
    CommandLineError,
    ConfigError,
    PDBAbortExecution,
    PDBInvalidCommandNameException,
    PDBInvalidSubCommandNameException,
    PDBStoreException,
)
from pdbstore.io.colors import init_colorama
from pdbstore.io.output import cli_out_write, Color, LEVEL_TRACE, PDBStoreOutput
from pdbstore.typing import Any, Dict, ExitCode, List, Optional


class Cli:
    """A single command of the PDBStore application, with all the first level commands.
    Manages the parsing of parameters and delegates functionality to the appropriate
    command. It can also show the help of the tool.
    """

    def __init__(self) -> None:
        self._groups: Dict[str, List[str]] = defaultdict(list)
        self._commands: Dict[str, Any] = {}
        init_colorama(sys.stderr)

    def _add_commands(self) -> None:
        pdbstore_commands_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "commands"
        )
        for module in pkgutil.iter_modules([pdbstore_commands_path]):
            module_name = module[1]
            self._add_command(f"pdbstore.cli.commands.{module_name}", module_name)

    def _add_command(
        self, import_path: str, method_name: str, package: Optional[str] = None
    ) -> None:
        try:
            imported_module = importlib.import_module(import_path)
            cmd_mapping = getattr(imported_module, "__MAPPING__", {})
            cb_name = cmd_mapping.get(method_name, method_name)
            command_wrapper = getattr(imported_module, cb_name)
            if command_wrapper.doc:
                name = f"{package}:{method_name}" if package else method_name
                self._commands[name] = command_wrapper
                self._groups[command_wrapper.group].append(name)
            for name, value in getmembers(imported_module):
                if isinstance(value, PDBStoreSubCommand):
                    if name.startswith(f"{cb_name}_"):
                        command_wrapper.add_subcommand(value)
                    elif name[0] != "_":
                        raise PDBStoreException(
                            "The name for the subcommand method should "
                            "begin with the main command name + '_'. "
                            f"i.e. {cb_name}_<subcommand_name>"
                        )
        except AttributeError as exc:
            raise PDBStoreException(
                f"There is no {method_name} method defined in {import_path}"
            ) from exc

    def _print_similar(self, command: str) -> None:
        """Looks for similar commands and prints them if found."""
        output = PDBStoreOutput()
        matches = get_close_matches(
            word=command, possibilities=self._commands.keys(), n=5, cutoff=0.75
        )

        if len(matches) == 0:
            return

        if len(matches) > 1:
            output.info("The most similar commands are")
        else:
            output.info("The most similar command is")

        for match in matches:
            output.info(f"    {match}")

        output.writeln("")

    def _output_help_cli(self) -> None:
        """
        Prints a summary of all commands.
        """
        max_len = max((len(c) for c in self._commands)) + 4
        line_format = f"{{: <{max_len}}}"

        for group_name, comm_names in sorted(self._groups.items()):
            cli_out_write("\n" + group_name + " commands", Color.YELLOW)
            for name in comm_names:
                # future-proof way to ensure tabular formatting
                cli_out_write(line_format.format(name), Color.GREEN, endline="")

                # Help will be all the lines up to the first empty one
                docstring_lines = self._commands[name].doc.split("\n")
                start = False
                data = []
                for line in docstring_lines:
                    line = line.strip()
                    if not line:
                        if start:
                            break
                        start = True
                        continue
                    data.append(line)

                txt = textwrap.fill(" ".join(data), 80, subsequent_indent=" " * (max_len + 2))
                cli_out_write(txt)

        cli_out_write("")
        cli_out_write('Type "pdbstore <command> -h" for help', Color.BLUE)

    def run(self, *args: Any) -> ExitCode:
        """Entry point for executing commands, dispatcher to class
        methods
        """
        output = PDBStoreOutput()
        self._add_commands()
        try:
            command_argument = args[0][0]
        except IndexError:  # No parameters
            self._output_help_cli()
            raise PDBInvalidCommandNameException(None)  # pylint: disable=raise-missing-from

        try:
            command = self._commands[command_argument]
        except KeyError:  # No parameters
            if command_argument in ["--version"]:
                cli_out_write(
                    f"{pdbstore_version}",
                    fore=Color.BRIGHT_GREEN,
                )
                raise PDBAbortExecution(0)  # pylint: disable=raise-missing-from

            if command_argument in ["-h", "--help"]:
                self._output_help_cli()
                raise PDBAbortExecution(0)  # pylint: disable=raise-missing-from

            output.info(
                f"'{command_argument}' is not a PDBStore command. " "See 'pdbstore --help'."
            )
            output.info("")
            self._print_similar(command_argument)
            raise PDBInvalidCommandNameException(  # pylint: disable=raise-missing-from
                command_argument
            )

        try:
            command.run(args[0][1:])
        except Exception as exc:
            if PDBStoreOutput.level_allowed(LEVEL_TRACE):
                output.trace("\n".join(traceback.format_exception(*sys.exc_info())))
            raise exc
        return 0

    @staticmethod
    def exception_exit_error(exception: Optional[BaseException]) -> ExitCode:
        """Convert exception into an exit code"""
        output = PDBStoreOutput()
        if exception is None:
            return SUCCESS
        if isinstance(exception, PDBAbortExecution):
            return SUCCESS if exception.exitcode == 0 else ERROR_ENCOUNTERED
        if isinstance(exception, PDBInvalidCommandNameException):
            return ERROR_COMMAND_NAME
        if isinstance(exception, PDBInvalidSubCommandNameException):
            return ERROR_SUBCOMMAND_NAME
        if isinstance(exception, CommandLineError):
            output.error(exception.message)
            return ERROR_UNEXPECTED
        if isinstance(exception, ConfigError):
            output.error(exception.message)
            return ERROR_INVALID_CONFIGURATION
        if isinstance(exception, PDBStoreException):
            output.error(exception.message)
            return ERROR_GENERAL
        if isinstance(exception, SystemExit):
            if exception.code != 0:
                output.error(f"Exiting with code: {exception.code}")
            return ERROR_ENCOUNTERED

        assert isinstance(exception, Exception)
        output.error(traceback.format_exc())
        try:
            msg = str(exception)
        except Exception:  # pylint: disable=broad-except
            msg = repr(exception)
        output.error(msg)
        return ERROR_UNEXPECTED


def main(args: Optional[List[str]] = None) -> ExitCode:
    """main entry point of the pdbstore application, using a Command to
    parse parameters.

    :parameters:
        :param args: Optional command-line arguments, else `sys.argv` will
                     be used by default

    :return: One of the following exit code:

    * 0: Success (done)
    * 1: General PDBStoreException error (done)
    * 2: Ctrl+C
    * 3: Ctrl+Break
    * 4: SIGTERM
    * 5: Invalid configuration (done)
    * 6: Unexpected error
    * 7: Invalid command name
    * 8: Invalid sub-command name
    """

    def ctrl_c_handler(_: Any, __: Any) -> None:
        print("You pressed Ctrl+C!")
        sys.exit(USER_CTRL_C)

    def sigterm_handler(_: Any, __: Any) -> None:
        print("Received SIGTERM!")
        sys.exit(ERROR_SIGTERM)

    def ctrl_break_handler(_: Any, __: Any) -> None:
        print("You pressed Ctrl+Break!")
        sys.exit(USER_CTRL_BREAK)

    signal.signal(signal.SIGINT, ctrl_c_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)

    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, ctrl_break_handler)

    cli = Cli()
    error: ExitCode = SUCCESS
    try:
        cli.run(args if args is not None else sys.argv[1:])
    except BaseException as exc:  # pylint: disable=broad-except
        error = cli.exception_exit_error(exc)
    return error

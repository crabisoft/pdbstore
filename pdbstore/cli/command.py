import argparse
import sys

from pdbstore.cli.once_argument import OnceArgument
from pdbstore.cli.smart_formatter import SmartFormatter
from pdbstore.config import ConfigParser
from pdbstore.const import ENV_PDBSTORE_CFG
from pdbstore.exceptions import (
    ConfigError,
    ParseFileError,
    PDBAbortExecution,
    PDBInvalidSubCommandNameException,
    PDBStoreException,
)
from pdbstore.io.file import build_files_list
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    SubParserType,
    Union,
)


class PDBStoreArgumentParser(argparse.ArgumentParser):
    """PDBStore argument parser to support configuration file"""

    _command: "PDBStoreCommand"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @staticmethod
    def _parse_value(key: str, value: Any, recursive: bool = False) -> Any:
        if key == "files":
            return build_files_list(value, recursive)

        if not isinstance(value, str) or not value.startswith("@"):
            return value

        # If the user-provided value starts with @, we try to read the file
        # path provided after @ as the real value. Exit on any error.
        try:
            with open(value[1:], "r", encoding="utf-8") as fpa:
                return fpa.readlines()
        except Exception as exf:
            raise ParseFileError(value[1:]) from exf

    def parse_args(  # type: ignore[override] # pylint: disable=arguments-differ
        self, args: Optional[Sequence[str]] = None
    ) -> argparse.Namespace:
        options = super().parse_args(args)

        PDBStoreOutput.define_log_level(options.verbosity)
        PDBStoreOutput.define_log_output(options.log_file)
        output = PDBStoreOutput()

        if "help" in options and options.help:
            self.print_help(output.stream)
            raise PDBAbortExecution(0)
        try:
            config = ConfigParser(options.store_id, options.config_file)
        except ConfigError as exc:
            if "--help" in (args or sys.argv) or "-h" in (args or sys.argv):
                self.print_help()
                raise PDBAbortExecution(0) from exc
            raise exc

        args_dict = vars(options)
        recursive = args_dict.get("recursive", False)
        for key, value in vars(options).items():
            if value is not None:
                args_dict[key] = self._parse_value(key, value, recursive)

        config.merge(args_dict)
        for (
            key,
            value,
        ) in config.__dict__.items():  # pylint: disable=invalid-name
            if value is not None:
                args_dict[key] = value

        if "input_store_id" in args_dict:
            input_store_name = args_dict.get("input_store_id")
            if input_store_name:
                args_dict["input_store_dir"] = config.get_store_directory(input_store_name)

        return argparse.Namespace(**args_dict)


CommandCallback = Callable[[PDBStoreArgumentParser, Any], Any]
"""Command callback function.
:param PDBStoreArgumentParser: Current parser object
:param Any: Command-line arguments as a list
:return: Depend on each command.
"""

SubCommandCallback = Callable[[PDBStoreArgumentParser, argparse.ArgumentParser, Any], Any]
"""Sub-command callback function.
:param PDBStoreArgumentParser: Current parser object
:param argparse.ArgumentParser: The command sub-parser object
:param Any: Command-line arguments as a list
:return: Depend on each command.
"""

FormatterCallback = Callable[[Any], None]
"""Formatter callback function.
    :param Dict: Output format keyword with its callback function function
"""


class BaseCommand:
    """Base PDBStore command"""

    def __init__(
        self,
        name: str,
        callback: Union[CommandCallback, SubCommandCallback],
        formatters: Optional[Dict[str, FormatterCallback]] = None,
    ) -> None:
        self.formatters: Dict[str, FormatterCallback] = {"text": lambda x: None}
        self.callback = callback
        self.callback_name: str = name
        if formatters:
            for kind, action in formatters.items():
                if callable(action):
                    self.formatters[kind] = action
                else:
                    raise PDBStoreException(
                        f"Invalid formatter for {kind}. The formatter must be" "a valid function"
                    )
        if callback.__doc__:
            self.callback_doc = callback.__doc__
        else:
            raise PDBStoreException(
                f"No documentation string defined for command: '{self.callback_name}'."
                " PDBStore commands should provide a documentation string explaining "
                "its use briefly."
            )

    @staticmethod
    def init_log_levels(parser: argparse.ArgumentParser) -> None:
        """Add verbosity command-line option"""
        parser.add_argument(
            "-V",
            "--verbosity",
            default="status",
            metavar="LEVEL",
            nargs="?",
            type=str,
            help="Level of detail of the output. Valid options from less verbose "
            "to more verbose: -Vquiet, -Verror, -Vwarning, -Vnotice, -Vstatus, "
            "-V or -Vverbose, -VV or -Vdebug, -VVV or -vtrace",
        )

    @staticmethod
    def init_log_file(parser: argparse.ArgumentParser) -> None:
        """Add output log file command-line option"""
        parser.add_argument(
            "-L",
            "--log-file",
            metavar="PATH",
            type=str,
            help="Send output to PATH instead of stderr.",
            action=OnceArgument,
        )

    @staticmethod
    def init_config(parser: argparse.ArgumentParser, single: bool = True) -> None:
        """Add configuration file command-line option"""
        parser.add_argument(
            "-C",
            "--config-file",
            metavar="PATH",
            dest="config_file",
            action="append",
            help=(
                "Configuration file to use. Can be used multiple times. "
                f"[env var: {ENV_PDBSTORE_CFG}]"
            ),
        )

        parser.add_argument(
            "-S",
            "--store",
            metavar="NAME",
            dest="store_id",
            type=str,
            help=(
                "Which configuration section should be used. "
                "If not defined, the default will be used"
            ),
            required=False,
            action=OnceArgument,
        )

        if not single:
            parser.add_argument(
                "-I",
                "--input-store",
                metavar="NAME",
                dest="input_store_id",
                type=str,
                help=("Which configuration section should be used as input store. "),
                required=False,
                action=OnceArgument,
            )

    @property
    def _help_formatters(self) -> List[str]:
        """
        Formatters that are shown as available in help, 'text' formatter
        should not appear
        """
        return [formatter for formatter in self.formatters if formatter != "text"]

    def init_formatters(self, parser: argparse.ArgumentParser) -> None:
        """Add formatters command-line options."""
        formatters = self._help_formatters
        if formatters:
            parser.add_argument(
                "-f",
                "--format",
                metavar="NAME",
                action=OnceArgument,
                help=f"Select the output format: {', '.join(formatters)}",
            )

    @property
    def name(self) -> str:
        """Get action name"""
        return self.callback_name

    @property
    def method(self) -> Union[CommandCallback, SubCommandCallback]:
        """Get action method"""
        return self.callback

    @property
    def doc(self) -> str:
        """Get action help message"""
        return self.callback_doc

    def _format(self, parser: argparse.ArgumentParser, info: Dict[str, Any], *args: Any) -> None:
        parser_args, _ = parser.parse_known_args(*args)

        default_format = "text"
        try:
            formatarg = parser_args.format or default_format
        except AttributeError:
            formatarg = default_format

        try:
            formatter = self.formatters[formatarg]
        except KeyError as exc:
            raise PDBStoreException(
                f"{formatarg} is not a known format. Supported formatters are: "
                f"{', '.join(self._help_formatters)}"
            ) from exc

        formatter(info)


class PDBStoreCommand(BaseCommand):
    """Main PDBStore command object"""

    def __init__(
        self,
        cb: CommandCallback,
        group: Optional[str] = None,
        formatters: Optional[Dict[str, FormatterCallback]] = None,
        callback_name: Optional[str] = None,
    ) -> None:
        if not callback_name:
            callback_name = cb.__name__.replace("_", "-")
        super().__init__(callback_name, cb, formatters=formatters)
        self.subcommands: Dict[str, "PDBStoreSubCommand"] = {}
        self.group_name = group or "Other"

    def add_subcommand(self, subcommand: "PDBStoreSubCommand") -> None:
        """Register new sub-command"""
        subcommand.set_name(self.callback_name)
        self.subcommands[subcommand.callback_name] = subcommand

    def _docs(self) -> PDBStoreArgumentParser:
        parser = PDBStoreArgumentParser(
            description=self.callback_doc,
            prog=f"pdbstore {self.callback_name}",
            formatter_class=SmartFormatter,
            add_help=False,
        )
        return parser

    def run(self, *args: Any) -> None:
        """Parse and execute requested command"""
        parser = PDBStoreArgumentParser(
            description=self.callback_doc,
            prog=f"pdbstore {self.callback_name}",
            formatter_class=SmartFormatter,
            add_help=False,
        )
        # pylint: disable=protected-access
        parser._command = self
        info = self.callback(parser, *args)

        if not self.subcommands:
            self._format(parser, info, *args)
        else:
            subcommand_parser: SubParserType = parser.add_subparsers(
                dest="subcommand",
            )
            subcommand_parser.required = True
            try:
                sub = self.subcommands[args[0][0]]
            except (KeyError, IndexError):  # display help
                for sub in self.subcommands.values():
                    sub.set_parser(subcommand_parser)
                parser.print_help()
                raise PDBInvalidSubCommandNameException(  # pylint: disable=raise-missing-from
                    args[0][0] if len(args[0]) else ""
                )

            sub.set_parser(subcommand_parser)
            sub.run(parser, *args)

    @property
    def group(self) -> str:
        """Gets group name."""
        return self.group_name


class PDBStoreSubCommand(BaseCommand):
    """PDBStore sub-command"""

    parser: argparse.ArgumentParser

    def __init__(
        self,
        cb: SubCommandCallback,
        formatters: Optional[Dict[str, FormatterCallback]] = None,
    ) -> None:
        super().__init__("", cb, formatters=formatters)
        self.subcommand_name = cb.__name__.replace("_", "-")

    def run(self, parent_parser: PDBStoreArgumentParser, *args: object) -> None:
        """Execute the sub-command"""
        setattr(self.parser, "_command", self)
        info = self.callback(parent_parser, self.parser, *args)
        self._format(parent_parser, info, *args)

    def set_name(self, parent_name: str) -> None:
        """Set sub-command name"""
        self.callback_name = self.subcommand_name.replace(f"{parent_name}-", "", 1)

    def set_parser(self, subcommand_parser: SubParserType) -> None:
        """Set the associated parser"""
        self.parser = subcommand_parser.add_parser(
            self.callback_name, help=self.callback_doc, add_help=True
        )
        self.parser.description = self.callback_doc


def pdbstore_command(
    group: str,
    formatters: Optional[Dict[str, FormatterCallback]] = None,
    name: Optional[str] = None,
) -> Callable[[CommandCallback], PDBStoreCommand]:
    """Register a PDBStore command"""
    return lambda f: PDBStoreCommand(f, group, formatters=formatters, callback_name=name)


def pdbstore_subcommand(
    formatters: Optional[Dict[str, FormatterCallback]] = None
) -> Callable[[SubCommandCallback], PDBStoreSubCommand]:
    """Register a PDBStore sub-command"""
    return lambda f: PDBStoreSubCommand(f, formatters=formatters)

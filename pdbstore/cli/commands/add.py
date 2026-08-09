from pathlib import Path

import pdbstore.io
from pdbstore.cli.args import (
    add_global_arguments,
    add_product_arguments,
    add_storage_arguments,
)
from pdbstore.cli.boolean_action import BooleanAction
from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
from pdbstore.cli.formatters import summary_json_formatter
from pdbstore.entities import Summary
from pdbstore.exceptions import (
    CommandLineError,
    CompressionNotSupportedError,
    PDBAbortExecution,
)
from pdbstore.factory import open_store
from pdbstore.io.output import cli_out_write
from pdbstore.typing import Any, Optional
from pdbstore.usecases.add import AddSymbolsInteractor


def add_text_formatter(summary: Summary) -> None:
    """Print output text for add command as simple text"""
    nb_deleted = summary.linked.count(True) if summary.linked else 0
    cli_out_write(f"Number of files stored = {summary.success(False)}")
    cli_out_write(f"Number of errors = {summary.failed(False)}")
    cli_out_write(f"Number of files ignored = {summary.skipped(False)}")
    cli_out_write(f"Number of transactions deleted = {nb_deleted}")

    if summary.failed(True):
        raise PDBAbortExecution(summary.failed(True))


@pdbstore_command(
    group="Storage",
    formatters={"text": add_text_formatter, "json": summary_json_formatter},
)
def add(parser: PDBStoreArgumentParser, *args: Any) -> Any:
    """
    Add files to local symbol store
    """
    add_product_arguments(parser)
    parser.add_argument(
        "-c",
        "--comment",
        metavar="COMMENT",
        type=str,
        help="Comment for the transaction.",
    )
    parser.add_argument(
        "-z",
        "--compress",
        action=BooleanAction,
        default=False,
        help="Store compressed files on the server. Defaults to False.",
    )

    add_storage_arguments(parser)

    parser.add_argument(
        "-k",
        "--keep-count",
        metavar="COUNT",
        dest="keep_count",
        type=int,
        help="""The maximum number of transactions to preserve and
        once the number of transcations exceeds, older transactions are removed.""",
    )

    parser.add_argument(
        "-F",
        "--force",
        dest="force",
        action="store_true",
        default=False,
        help="""Overwrite any existing file from the store. uses file's hash
        to check if it's already exists in the store. Defaults to False.""",
    )

    parser.add_argument(
        "-r",
        "--recursive",
        dest="recursive",
        default=False,
        action="store_true",
        help="Add files or directories recursively.",
    )

    parser.add_argument(
        "files",
        metavar="FILE_OR_DIR",
        type=str,
        nargs="*",
        help="""Network path of files or directories to add.
        If the named file begins with an '@' symbol, it is treated
        as a response file which is expected to contain a list of
        files (path and filename, 1 entry per line) to be stored.""",
    )

    add_global_arguments(parser)

    opts = parser.parse_args(*args)

    # Check input configuration and arguments
    store_dir = opts.store_dir
    if not store_dir:
        raise CommandLineError("no symbol store directory given")

    product_name: Optional[str] = opts.product_name
    if not product_name:
        raise CommandLineError("no product name given")

    product_version: Optional[str] = opts.product_version
    if not product_version:
        raise CommandLineError("no product version given")

    input_files = opts.files
    if not input_files:
        raise CommandLineError("no file or directory given")

    compress: bool = opts.compress
    if compress and not pdbstore.io.is_compression_supported():
        raise CompressionNotSupportedError()

    return AddSymbolsInteractor(open_store(store_dir)).execute(
        [Path(file) for file in input_files],
        product_name,
        product_version,
        opts.comment or "",
        compress,
        opts.force,
        opts.keep_count or 0,
    )

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
from pdbstore.exceptions import (
    CommandLineError,
    CompressionNotSupportedError,
    PDBAbortExecution,
    PDBStoreException,
    UnknowFileTypeError,
)
from pdbstore.io.output import cli_out_write, PDBStoreOutput
from pdbstore.store import OpStatus, Store, Summary, TransactionType
from pdbstore.typing import Any, Optional


def add_text_formatter(summary: Summary) -> None:
    """Print output text for add command as simple text"""
    cli_out_write(f"Number of files stored = {summary.success(False)}")
    cli_out_write(f"Number of errors = {summary.failed(False)}")
    cli_out_write(f"Number of files ignored = {summary.skipped(False)}")
    cli_out_write(f"Number of transactions deleted = {summary.count(True)-1}")

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

    output = PDBStoreOutput()
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

    compress: bool = opts.compress or False
    if compress and not pdbstore.io.is_compression_supported():
        raise CompressionNotSupportedError()
    store = Store(store_dir)
    # Generate next transaction id
    store.next_transaction_id  # pylint: disable=pointless-statement

    # New transaction object to store all assocaited files
    comment: Optional[str] = opts.comment or ""
    new_transaction = store.new_transaction(
        product_name,
        product_version,
        comment,
    )

    success = 0
    errors_list = []
    for file in input_files:
        try:
            if new_transaction.register_entry(Path(file), compress):
                success += 1
        except UnknowFileTypeError as exu:
            output.warning(f"{file}: not a known file type")
            errors_list.append([file, str(exu)])
        except PDBStoreException as exp:
            output.error(str(exp))
            errors_list.append([file, str(exp)])
        except Exception as exg:  # pylint: disable=broad-except # pragma: no cover
            errors_list.append([file, str(exg)])
            output.error(f"unexpected error when adding {file} with the following error:")
            output.error(exg)

    if success > 0:
        # Commit modifications to the disk
        try:
            summary = store.commit(new_transaction, opts.force or False)
        except PDBStoreException as exc:
            output.error(exc)
            return Summary(new_transaction.id, OpStatus.FAILED, TransactionType.ADD)
        except Exception:  # pylint: disable=broad-except
            output.error(
                "unexpected error when filling Transaction object",
            )
    else:
        summary = Summary(None, OpStatus.SKIPPED, TransactionType.ADD)

    for error in errors_list:
        summary.add_file(error[0], OpStatus.FAILED, error[1])
    # Clean oldest version
    keep_count = opts.keep_count or 0
    head = summary
    if keep_count > 0:
        summary_clean = store.remove_old_versions(product_name, product_version, keep_count)
        head.linked = summary_clean
        head = summary_clean

    return summary

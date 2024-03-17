import json
import os

from pdbstore import util
from pdbstore.cli.args import add_global_arguments, add_storage_arguments
from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
from pdbstore.exceptions import (
    CommandLineError,
    FileNotExistsError,
    InvalidPEFile,
    PDBAbortExecution,
    PDBStoreException,
)
from pdbstore.io.output import cli_out_write, PDBStoreOutput
from pdbstore.store import (
    OpStatus,
    Store,
    Summary,
    Transaction,
    TransactionEntry,
    TransactionType,
)
from pdbstore.typing import Any, Optional, Tuple


def fetch_text_formatter(summary: Summary) -> None:
    """Print output text from a Summary object as TEXT format"""
    display_full_path = getattr(summary, "full_name", False)
    input_len = 80
    if display_full_path:
        for cur in summary.iterator():
            for queryd in cur.files:
                symbol_path = queryd.get("path", "")
                file_path = queryd.get("input", "")
                if not file_path:
                    file_path = symbol_path
                    symbol_path = None
                file_len = len(symbol_path or file_path)
                if (file_len + 2) > input_len:
                    input_len = file_len + 2

    cli_out_write(f"{'Input File':<{input_len}s}{'Compressed':^10s} Symbol File")
    for cur in summary.iterator():
        for queryd in cur.files:
            symbol_path = queryd.get("path", "")
            file_path = queryd.get("input", "")
            if not file_path:
                file_path = symbol_path
                symbol_path = None
            status: OpStatus = OpStatus.from_str(queryd.get("status", OpStatus.SKIPPED))
            error_msg = queryd.get("error")

            if not display_full_path:
                if symbol_path and status == OpStatus.SUCCESS:
                    symbol_path = util.abbreviate(symbol_path, 80)
                file_path = util.abbreviate(file_path, 80)

            if status == OpStatus.SUCCESS:
                compressed = "Yes" if queryd.get("compressed", False) else "No"
                cli_out_write(f"{str(file_path):<{input_len}s}{compressed:^10s} {symbol_path}")
            elif status == OpStatus.SKIPPED:
                cli_out_write(f"{str(file_path):<{input_len}s}{'':^10s} {error_msg or 'Not found'}")
            else:
                cli_out_write(
                    f"{str(file_path):<{input_len}s}{'':^10s} {error_msg or 'File not found'}"
                )

    total = summary.failed(True)
    if total > 0:
        raise PDBAbortExecution(total)


def fetch_json_formatter(summary: Summary) -> None:
    """Print output text from a Summary object as JSON format"""
    out = []
    head: Optional[Summary] = summary
    while head:
        dct = {
            "id": head.transaction_id,
            "type": head.transaction_type.value if head.transaction_type else "undefined",
            "status": head.status.value,
            "success": head.success(False),
            "failure": head.failed(True),
            "skip": head.skipped(True),
            "files": head.files,
            "message": head.error_msg or "",
        }
        out.append(dct)
        head = head.linked

    cli_out_write(json.dumps(out, indent=4))

    total = summary.failed(True)
    if total > 0:
        raise PDBAbortExecution(total)


@pdbstore_command(
    group="Usage",
    formatters={"text": fetch_text_formatter, "json": fetch_json_formatter},
)
def fetch(parser: PDBStoreArgumentParser, *args: Any) -> Any:
    """
    Fetch all files from a symbol store
    """
    add_storage_arguments(parser)

    parser.add_argument(
        "-r",
        "--recursive",
        dest="recursive",
        default=False,
        action="store_true",
        help="Add files or directories recursively.",
    )

    parser.add_argument(
        "-O",
        "--output",
        metavar="DIR",
        dest="output_dir",
        default=None,
        action="store",
        help="Store requested files into DIR instead near from the input file.",
    )

    parser.add_argument(
        "-F",
        "--full-name",
        dest="full_name",
        default=False,
        action="store_true",
        help="Display file path without abbreviation.",
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

    input_files = opts.files
    if not input_files:
        raise CommandLineError("no file or directory given")

    output_dir = opts.output_dir

    store = Store(store_dir)

    output.verbose(f"Search pdb files for {len(input_files)} file(s)")

    # Check for each file is present to the specified store or not.
    summary = Summary(None, OpStatus.SUCCESS, TransactionType.FETCH)
    if opts.full_name:
        setattr(summary, "full_name", True)

    for file_path in input_files:
        try:
            entry: Optional[Tuple[Transaction, TransactionEntry]] = store.fetch_symbol(file_path)
            if not entry:
                summary.add_file(file_path, OpStatus.SKIPPED, "Not found")
                continue

            symbol_path = entry[1].extract(
                output_dir or os.path.dirname(util.path_to_str(file_path))
            )
            if symbol_path:
                dct = summary.add_file(util.path_to_str(symbol_path), OpStatus.SUCCESS)
                dct["input"] = util.path_to_str(file_path)
            else:
                summary.add_file(
                    util.path_to_str(file_path),
                    OpStatus.FAILED,
                    f"Failed to extract from transaction {entry[0].transaction_id}",
                )
        except InvalidPEFile:
            summary.add_file(util.path_to_str(file_path), OpStatus.SKIPPED, "Not a valid pe file")
        except FileNotExistsError:
            summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, "File not found")
        except PDBStoreException as exp:  # pragma: no cover
            summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, "ex:" + str(exp))
        except Exception as exc:  # pylint: disable=broad-except # pragma: no cover
            summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, str(exc))
            output.error(exc)
            output.error(f"unexpected error when fetching information for {file_path}")
    return summary

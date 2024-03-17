import json

from pdbstore import util
from pdbstore.cli.args import add_global_arguments, add_storage_arguments
from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
from pdbstore.exceptions import (
    CommandLineError,
    FileNotExistsError,
    PDBAbortExecution,
    PDBStoreException,
    UnknowFileTypeError,
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
from pdbstore.typing import Any, List, Optional, Tuple


def query_text_formatter(summary: Summary) -> None:
    """Print output text from a Summary object as TEXT format"""
    display_full_path = getattr(summary, "full_name", False)
    input_len = 80
    if display_full_path:
        for cur in summary.iterator():
            for queryd in cur.files:
                file_path = queryd.get("path", "")
                input_path = queryd.get("input", "")
                if file_path:
                    if (
                        OpStatus.from_str(queryd.get("status", OpStatus.SKIPPED))
                        == OpStatus.SUCCESS
                    ):
                        file_len = len(input_path)
                    else:
                        file_len = len(file_path)
                    if (file_len + 2) > input_len:
                        input_len = file_len + 2

    cli_out_write(f"{'Input File':<{input_len}s}{'Compressed':^10s} Symbol File")
    for cur in summary.iterator():
        for queryd in cur.files:
            file_path = queryd.get("path", "")
            input_path = queryd.get("input", "")
            status: OpStatus = OpStatus.from_str(queryd.get("status", OpStatus.SKIPPED))
            error_msg = queryd.get("error")

            if not file_path:
                continue

            if not display_full_path:
                if input_path and status == OpStatus.SUCCESS:
                    input_path = util.abbreviate(input_path, 80)

                file_path = util.abbreviate(file_path, 80)

            if status == OpStatus.SUCCESS:
                compressed = "Yes" if queryd.get("compressed", False) else "No"
                cli_out_write(f"{input_path:<{input_len}s}{compressed:^10s} {file_path}")
            elif status == OpStatus.SKIPPED:
                cli_out_write(f"{file_path:<{input_len}s}{'':^10s} {error_msg or 'Not found'}")
            else:
                cli_out_write(f"{file_path:<{input_len}s}{'':^10s} {error_msg or 'File not found'}")

    total = summary.failed(True) + summary.skipped(True)
    if total > 0:
        raise PDBAbortExecution(total)


def query_json_formatter(summary: Summary) -> None:
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
            "message": head.error_msg,
        }
        out.append(dct)
        head = head.linked

    cli_out_write(json.dumps(out, indent=4))

    total = summary.failed(True) + summary.skipped(True)
    if total > 0:
        raise PDBAbortExecution(total)


@pdbstore_command(
    group="Usage",
    formatters={"text": query_text_formatter, "json": query_json_formatter},
)
def query(parser: PDBStoreArgumentParser, *args: Any) -> Any:
    """
    Check if file(s) are indexed on the server
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

    store = Store(store_dir)

    output.verbose(f"Query record for {len(input_files)} file(s)")

    # Check for each file is present to the specified store or not.
    summary = Summary(None, OpStatus.SUCCESS, TransactionType.QUERY)
    if opts.full_name:
        setattr(summary, "full_name", True)

    for file_path in input_files:
        try:
            entries: List[Tuple[Transaction, TransactionEntry]] = store.find_entries(file_path)
            if entries:
                summary.add_entry(
                    entries[0][1],
                    OpStatus.SUCCESS,
                    entries[0][0].transaction_type,
                    None,
                    compressed=entries[0][1].compressed,
                    input=util.path_to_str(file_path),
                )
            else:
                summary.add_file(
                    util.path_to_str(file_path),
                    OpStatus.SKIPPED,
                )
        except UnknowFileTypeError:
            summary.add_file(util.path_to_str(file_path), OpStatus.SKIPPED, "Not a known file type")
        except FileNotExistsError:
            summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, "File not found")
        except PDBStoreException as exp:
            summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, "ex:" + str(exp))
        except Exception as exc:  # pylint: disable=broad-except # pragma: no cover
            summary.add_file(util.path_to_str(file_path), OpStatus.FAILED, str(exc))
            output.error(f"unexpected error when querying information for {file_path}")
    return summary

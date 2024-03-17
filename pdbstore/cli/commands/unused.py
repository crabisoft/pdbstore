import json
import os
import time
from pathlib import Path

from pdbstore import util
from pdbstore.cli.args import add_global_arguments, add_storage_arguments
from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
from pdbstore.exceptions import CommandLineError, PDBAbortExecution, PDBStoreException
from pdbstore.io.output import cli_out_write, PDBStoreOutput
from pdbstore.store import OpStatus, Store, Summary, TransactionType
from pdbstore.typing import Any


def unused_text_formatter(summary: Summary) -> None:
    """Print output text from a Summary object as TEXT format"""
    if len(summary.files) == 0:
        return

    input_len = 80
    cli_out_write(f"{'Input File':<{input_len}s}{'Date':^10s}  Transaction ID")
    for cur in summary.iterator():
        files_list = sorted(cur.files, key=lambda k: k.get("date", "N/A"))
        for file_entry in files_list:
            file_path = file_entry.get("path", "")
            file_date = file_entry.get("date", "N/A")
            transaction_id = file_entry.get("transaction_id", "N/A")
            status: OpStatus = OpStatus.from_str(file_entry.get("status", OpStatus.SKIPPED))
            error_msg = file_entry.get("error")

            file_path = util.abbreviate(file_path, 80)

            if status == OpStatus.SUCCESS:
                cli_out_write(f"{str(file_path):<{input_len}s}{file_date:^10s}  {transaction_id}")
            else:
                cli_out_write(
                    f"{str(file_path):<{input_len}s}{'N/A':^10s}  {error_msg or 'File not found'}"
                )

    total = summary.failed(True)
    if total > 0:
        raise PDBAbortExecution(total)


def unused_json_formatter(summary: Summary) -> None:
    """Print output text from a Summary object as JSON format"""
    if len(summary.files) == 0:
        cli_out_write("[]")
        return

    out = []
    for cur in summary.iterator():
        dct = {
            "status": cur.status.value,
            "success": cur.success(False),
            "failure": cur.failed(True),
            "skip": cur.skipped(True),
            "files": sorted(cur.files, key=lambda k: k.get("date", "N/A")),
            "message": cur.error_msg or "",
        }
        out.append(dct)

    cli_out_write(json.dumps(out, indent=4))

    total = summary.failed(True)
    if total > 0:
        raise PDBAbortExecution(total)


@pdbstore_command(
    group="Analysis",
    formatters={"text": unused_text_formatter, "json": unused_json_formatter},
)
def unused(parser: PDBStoreArgumentParser, *args: Any) -> Any:
    """
    Find all files not used since a specific date
    """
    add_storage_arguments(parser)

    parser.add_argument(
        "date",
        metavar="DATE",
        nargs="?",
        type=str,
        help="""Date given YYYY-MM-DD format.""",
    )

    add_global_arguments(parser)

    opts = parser.parse_args(*args)

    output = PDBStoreOutput()

    # Check input configuration and arguments
    store_dir = opts.store_dir
    if not store_dir:
        raise CommandLineError("no symbol store directory given")

    input_date = opts.date
    if not input_date:
        raise CommandLineError("no date given")

    store = Store(store_dir)

    try:
        input_date = time.strptime(input_date, "%Y-%m-%d")
    except ValueError as vexc:
        raise CommandLineError(f"'{input_date}' invalid date given") from vexc

    output.verbose(f"Search files not used since {input_date}")
    input_date = time.mktime(input_date)

    # Check for each file is present to the specified store or not.
    summary = Summary(None, OpStatus.SUCCESS, TransactionType.UNUSED)

    for transaction, entry in store.iterator(lambda x: not x.is_deleted()):
        try:
            output.verbose(f"checking {entry.rel_path} ...")
            file_path: Path = entry.stored_path
            file_stat: os.stat_result = file_path.stat()
            if file_stat.st_atime < input_date:
                dct = summary.add_file(entry.rel_path, OpStatus.SUCCESS)
                dct["date"] = time.strftime("%Y-%m-%d", time.localtime(file_stat.st_atime))
                dct["transaction_id"] = transaction.id
        except PDBStoreException as exp:  # pragma: no cover
            summary.add_file(util.path_to_str(entry.rel_path), OpStatus.FAILED, "ex:" + str(exp))
        except Exception as exc:  # pylint: disable=broad-except # pragma: no cover
            summary.add_file(util.path_to_str(entry.rel_path), OpStatus.FAILED, str(exc))
            output.error(exc)
            output.error("unexpected error when checking {file_path} file usage")

    return summary

import json
import time
from datetime import datetime, timedelta

from pdbstore import util
from pdbstore.cli.args import add_global_arguments, add_storage_arguments
from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
from pdbstore.entities import OpStatus, Summary
from pdbstore.exceptions import CommandLineError, PDBAbortExecution
from pdbstore.factory import open_store
from pdbstore.io.output import cli_out_write, PDBStoreOutput
from pdbstore.typing import Any
from pdbstore.usecases.unused import FindUnusedFilesInteractor


def unused_text_formatter(summary: Summary) -> None:
    """Print output text from a Summary object as TEXT format"""
    if len(summary.files) == 0:
        return

    input_len = 80
    total_size = 0
    clean_size = 0
    cli_out_write(f"{'Input File':<{input_len}s}{'Date':^10s}  Transaction ID")
    for cur in summary.iterator():
        files_list = sorted(cur.files, key=lambda k: k.get("date", "N/A"))
        for file_entry in files_list:
            file_path = file_entry.get("path", "")
            file_date = file_entry.get("date", "N/A")
            transaction_id = file_entry.get("transaction_id", "N/A")
            status: OpStatus = OpStatus.from_str(file_entry.get("status", OpStatus.SKIPPED))
            error_msg = file_entry.get("error")
            total_size += file_entry.get("file_size", 0)
            clean_size += file_entry.get("del_size", 0)

            file_path = util.abbreviate(file_path, 80)

            if status == OpStatus.SUCCESS:
                cli_out_write(f"{str(file_path):<{input_len}s}{file_date:^10s}  {transaction_id}")
            else:
                cli_out_write(
                    f"{str(file_path):<{input_len}s}{'N/A':^10s}  {error_msg or 'File not found'}"
                )

    if clean_size > 0:
        cli_out_write(f"\n{clean_size} bytes deleted")
    else:
        cli_out_write(f"\n{total_size} bytes can be deleted")
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
        total_size = 0
        clean_size = 0
        for file_entry in cur.files:
            total_size += file_entry.get("file_size", 0)
            clean_size += file_entry.get("del_size", 0)

        dct = {
            "status": cur.status.value,
            "success": cur.success(False),
            "failure": cur.failed(True),
            "skip": cur.skipped(True),
            "files": sorted(cur.files, key=lambda k: k.get("date", "N/A")),
            "message": cur.error_msg or "",
            "file_size": total_size + clean_size,
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
    Find all files not used based on the last access time of the files.
    """
    add_storage_arguments(parser)

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--date",
        metavar="YY-MM-DDDD",
        dest="date",
        type=str,
        help="""Find all files that were last accessed before the specified date.""",
    )
    group.add_argument(
        "--days",
        metavar="DAYS",
        dest="days",
        type=str,
        help="""Find all files that were last accessed before today minus the
                amount of days specified by 'DAYS'.""",
    )

    parser.add_argument(
        "-d",
        "--delete",
        dest="delete",
        action="store_true",
        help="""Delete automatically all unused files.""",
    )

    add_global_arguments(parser)

    opts = parser.parse_args(*args)

    output = PDBStoreOutput()

    # Check input configuration and arguments
    store_dir = opts.store_dir
    if not store_dir:
        raise CommandLineError("no symbol store directory given")

    input_date = opts.date
    input_days = opts.days

    if not input_date and not input_days:
        raise CommandLineError("no date or days given")

    if input_date:
        try:
            input_date = time.strptime(input_date, "%Y-%m-%d")
        except ValueError as vexc:
            raise CommandLineError(f"'{input_date}' invalid date given") from vexc
    else:
        try:
            input_date = (datetime.today() - timedelta(days=int(input_days))).timetuple()
        except ValueError as vexc:
            raise CommandLineError(f"'{input_days}' invalid days given") from vexc

    output.verbose(f"Search files not used since {time.strftime('%Y-%m-%d', input_date)}")

    return FindUnusedFilesInteractor(open_store(store_dir)).execute(
        time.mktime(input_date), opts.delete
    )

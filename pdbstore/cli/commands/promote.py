import json

from pdbstore import util
from pdbstore.cli.args import add_global_arguments, add_storage_arguments
from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
from pdbstore.exceptions import CommandLineError, PDBAbortExecution, PDBStoreException
from pdbstore.io.output import cli_out_write, PDBStoreOutput
from pdbstore.store import OpStatus, Store, Summary, TransactionType
from pdbstore.typing import Any, Optional


def promote_text_formatter(summary: Summary) -> None:
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
                cli_out_write(
                    f"{str(file_path):<{input_len}s}{compressed:^10s} {symbol_path}"
                )
            elif status == OpStatus.SKIPPED:
                cli_out_write(
                    f"{str(file_path):<{input_len}s}{'':^10s} {error_msg or 'Not found'}"
                )
            else:
                cli_out_write(
                    f"{str(file_path):<{input_len}s}{'':^10s} {error_msg or 'File not found'}"
                )

    total = summary.failed(True)
    if total > 0:
        raise PDBAbortExecution(total)


def promote_json_formatter(summary: Summary) -> None:
    """Print output text from a Summary object as JSON format"""
    out = []
    head: Optional[Summary] = summary
    while head:
        dct = {
            "id": head.transaction_id,
            "type": head.transaction_type.value
            if head.transaction_type
            else "undefined",
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
    group="Storage",
    formatters={"text": promote_text_formatter, "json": promote_json_formatter},
)
def promote(parser: PDBStoreArgumentParser, *args: Any) -> Any:
    """
    Promote one transaction from a snapshot to release store
    """
    parser.add_argument(
        "transaction_id",
        metavar="ID",
        type=int,
        nargs="*",
        help="Transaction ID string.",
    )

    parser.add_argument(
        "-c",
        "--comment",
        metavar="COMMENT",
        type=str,
        help="Comment for the transaction.",
    )

    add_storage_arguments(parser, False)

    parser.add_argument(
        "-F",
        "--force",
        dest="force",
        action="store_true",
        help="""Overwrite any existing file from the store. uses file's hash
        to check if it's already exists in the store. Defaults to False.""",
    )

    add_global_arguments(parser, single=False)

    opts = parser.parse_args(*args)

    output = PDBStoreOutput()

    # Check input configuration and arguments
    output_store_dir = opts.store_dir
    if not output_store_dir:
        raise CommandLineError("no symbol store directory given as output store")

    input_store_dir = opts.input_store_dir
    if not input_store_dir:
        raise CommandLineError("no symbol store directory given as input store")

    transaction_id = opts.transaction_id
    if not transaction_id:
        raise CommandLineError("no transaction ID given")

    store_in = Store(input_store_dir)
    store_out = Store(output_store_dir)

    summary: Summary
    summary_head: Optional[Summary] = None

    for trans_id in (
        transaction_id if isinstance(transaction_id, list) else [transaction_id]
    ):
        try:
            trans_in = store_in.find_transaction(transaction_id, TransactionType.ADD)
            summary_trans = store_out.promote_transaction(trans_in, opts.comment)
        except PDBStoreException as pdbse:
            summary_trans = Summary(trans_id, OpStatus.FAILED, None, str(pdbse))
        except Exception as exc:  # pylint: disable=broad-except # pragma: no cover
            summary_trans = Summary(trans_id, OpStatus.FAILED, None, str(exc))
            output.error(f"unexpected error when promoting {transaction_id}")
            output.error(exc)

        if summary_head:
            summary.linked = (  # noqa: F821 # pylint: disable=used-before-assignment
                summary_trans
            )
        else:
            summary_head = summary_trans
        summary = summary_trans

    return summary

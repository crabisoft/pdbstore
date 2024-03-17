from pdbstore.cli.args import add_global_arguments, add_storage_arguments
from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
from pdbstore.cli.formatters import summary_json_formatter
from pdbstore.exceptions import CommandLineError, PDBAbortExecution, PDBStoreException
from pdbstore.io.output import cli_out_write, PDBStoreOutput
from pdbstore.store import OpStatus, Store, Summary, TransactionType
from pdbstore.typing import Any, Optional


def promote_text_formatter(summary: Summary) -> None:
    """Print output text from a Summary object as TEXT format"""
    cli_out_write(f"Number of files promoted = {summary.success(False)}")
    cli_out_write(f"Number of errors = {summary.failed(False)}")

    if summary.failed(True):
        raise PDBAbortExecution(summary.failed(True))


@pdbstore_command(
    group="Storage",
    formatters={"text": promote_text_formatter, "json": summary_json_formatter},
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

    parser.add_argument(
        "-d",
        "--display-full-name",
        dest="full_name",
        default=False,
        action="store_true",
        help="Display file path without abbreviation.",
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

    for trans_id in transaction_id if isinstance(transaction_id, list) else [transaction_id]:
        try:
            trans_in = store_in.find_transaction(trans_id, TransactionType.ADD)
            summary_trans = store_out.promote_transaction(trans_in, opts.comment)
        except PDBStoreException as pdbse:
            summary_trans = Summary(trans_id, OpStatus.FAILED, None, str(pdbse))
        except Exception as exc:  # pylint: disable=broad-except # pragma: no cover
            summary_trans = Summary(trans_id, OpStatus.FAILED, None, str(exc))
            output.error(f"unexpected error when promoting {trans_id}")
            output.error(exc)

        if summary_head:
            summary.linked = summary_trans  # noqa: F821 # pylint: disable=used-before-assignment
        else:
            summary_head = summary_trans
        summary = summary_trans

    return summary

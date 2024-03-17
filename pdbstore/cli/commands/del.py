from pdbstore.cli.args import add_global_arguments, add_storage_arguments
from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
from pdbstore.cli.formatters import summary_json_formatter
from pdbstore.exceptions import CommandLineError, PDBAbortExecution, PDBStoreException
from pdbstore.io.output import cli_out_write, PDBStoreOutput
from pdbstore.store import OpStatus, Store, Summary, TransactionType
from pdbstore.typing import Any, Optional

__MAPPING__ = {"del": "delete"}


def del_text_formatter(summary: Summary) -> None:
    """Print output text for del command as simple text"""
    cli_out_write(f"Number of references deleted = {summary.referenced(True)}")
    cli_out_write(f"Number of files deleted = {summary.success(True)}")
    cli_out_write(f"Number of errors = {summary.failed(True)}")
    cli_out_write(f"Number of transactions deleted = {summary.count(True)}")

    if summary.failed(True):
        raise PDBAbortExecution(summary.failed(True))


@pdbstore_command(
    group="Storage",
    formatters={"text": del_text_formatter, "json": summary_json_formatter},
    name="del",
)
def delete(parser: PDBStoreArgumentParser, *args: Any) -> Any:
    """
    Delete files from local symbol store
    """

    parser.add_argument(
        "transaction_id",
        metavar="ID",
        type=int,
        nargs="*",
        help="Transaction ID string.",
    )

    add_storage_arguments(parser)
    add_global_arguments(parser)

    opts = parser.parse_args(*args)

    output = PDBStoreOutput()
    # Check input configuration and arguments
    store_dir = opts.store_dir
    if not store_dir:
        raise CommandLineError("no symbol store directory given")

    transaction_id = opts.transaction_id
    if not transaction_id:
        raise CommandLineError("no transaction ID given")

    store = Store(store_dir)
    # Generate next transaction id
    store.next_transaction_id  # pylint: disable=pointless-statement

    # Delete the transaction from the store
    summary: Summary
    summary_head: Optional[Summary] = None

    for trans_id in transaction_id if isinstance(transaction_id, list) else [transaction_id]:
        try:
            summary_del: Summary = store.delete_transaction(trans_id)
        except PDBStoreException as exp:
            output.error(str(exp))
            summary_del = Summary(trans_id, OpStatus.FAILED, TransactionType.DEL, str(exp))
        except BaseException as exg:  # pylint: disable=broad-exception-caught # pragma: no cover
            summary_del = Summary(trans_id, OpStatus.FAILED, TransactionType.DEL, str(exg))
            output.error(
                f"unexpected error when deleting {trans_id} transaction",
            )
        if summary_head:
            summary.linked = summary_del  # noqa: F821 # pylint: disable=used-before-assignment
        else:
            summary_head = summary_del
        summary = summary_del

    return summary

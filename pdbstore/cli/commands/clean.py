from pdbstore.cli.args import (
    add_global_arguments,
    add_product_arguments,
    add_storage_arguments,
)
from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
from pdbstore.cli.formatters import summary_json_formatter
from pdbstore.exceptions import CommandLineError, PDBAbortExecution
from pdbstore.io.output import cli_out_write, PDBStoreOutput
from pdbstore.store import OpStatus, Store, Summary, TransactionType
from pdbstore.typing import Any, Optional


def clean_text_formatter(summary: Summary) -> None:
    """Print output text for del command as simple text"""
    cli_out_write(f"Number of references deleted = {summary.referenced(True)}")
    cli_out_write(f"Number of files deleted = {summary.success(True)}")
    cli_out_write(f"Number of errors = {summary.failed(True)}")
    cli_out_write(f"Number of transactions deleted = {summary.count(True)}")

    if summary.failed(True):
        raise PDBAbortExecution(summary.failed(True))


@pdbstore_command(
    group="Storage",
    formatters={"text": clean_text_formatter, "json": summary_json_formatter},
)
def clean(parser: PDBStoreArgumentParser, *args: Any) -> Any:
    """
    Remove old transactions associated given some criteria
    """
    add_storage_arguments(parser)
    add_product_arguments(parser)

    parser.add_argument(
        "-c",
        "--comment",
        metavar="COMMENT",
        type=str,
        help="Comment to be search.",
    )
    parser.add_argument(
        "-k",
        "--keep",
        dest="keep_count",
        type=int,
        help="""The maximum number of transactions to preserve and once the number"
        of transcations exceeds, older transactions are removed.""",
    )

    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        default=False,
        action="store_true",
        help="Don't remove transactions/files from the symbol store.",
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
    keep_count: Optional[int] = opts.keep_count
    if keep_count is None:
        raise CommandLineError("keep_count value cannot be None")
    if keep_count < 0:
        output.debug("keep all transactions since keep_count is less than 0")
        return Summary(
            None,
            OpStatus.SUCCESS,
            TransactionType.DEL,
            "keep all transactions since keep_count is less than 0",
        )

    comment: Optional[str] = opts.comment
    dry_run: bool = opts.dry_run

    store = Store(store_dir)

    # Delete the transaction from the store
    summary = store.remove_old_versions(product_name, product_version, keep_count, comment, dry_run)

    return summary

from pdbstore.cli.args import add_global_arguments, add_storage_arguments
from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
from pdbstore.cli.formatters import summary_json_formatter
from pdbstore.entities import OpStatus, Summary, TransactionType
from pdbstore.exceptions import CommandLineError, PDBAbortExecution, PDBStoreException
from pdbstore.factory import open_store
from pdbstore.io.output import cli_out_write, PDBStoreOutput
from pdbstore.typing import Any, List
from pdbstore.usecases import lookup
from pdbstore.usecases.delete import chain_summaries
from pdbstore.usecases.promote import PromoteTransactionInteractor


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

    state_in = open_store(input_store_dir)
    state_out = open_store(output_store_dir)

    interactor = PromoteTransactionInteractor(state_out)
    summaries: List[Summary] = []

    for trans_id in transaction_id if isinstance(transaction_id, list) else [transaction_id]:
        try:
            trans_in = lookup.find_transaction(state_in.transactions, trans_id, TransactionType.ADD)
            summaries.append(interactor.execute(trans_in, state_in.gateway, opts.comment))
        except PDBStoreException as pdbse:
            summaries.append(Summary(trans_id, OpStatus.FAILED, None, str(pdbse)))
        except Exception as exc:  # pylint: disable=broad-except # pragma: no cover
            summaries.append(Summary(trans_id, OpStatus.FAILED, None, str(exc)))
            output.error(f"unexpected error when promoting {trans_id}")
            output.error(exc)

    return chain_summaries(summaries) if summaries else None

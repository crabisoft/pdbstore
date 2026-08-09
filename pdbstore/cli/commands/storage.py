import argparse

from pdbstore.cli.args import add_global_arguments, add_storage_arguments
from pdbstore.cli.command import (
    pdbstore_command,
    pdbstore_subcommand,
    PDBStoreArgumentParser,
)
from pdbstore.cli.formatters import summary_json_formatter
from pdbstore.drivers.blob.factory import create_blob_store
from pdbstore.entities import Summary
from pdbstore.exceptions import CommandLineError, PDBAbortExecution
from pdbstore.io.output import cli_out_write
from pdbstore.typing import Any, Tuple
from pdbstore.usecases.gateways.blob_store import BlobStore
from pdbstore.usecases.storage import MigrateStorageInteractor, VerifyStorageInteractor


def migrate_text_formatter(summary: Summary) -> None:
    """Print output text for the migrate sub-command as simple text"""
    cli_out_write(f"Number of files transferred = {summary.success(True)}")
    cli_out_write(f"Number of files already present = {summary.skipped(True)}")
    cli_out_write(f"Number of errors = {summary.failed(True)}")

    if summary.failed(True):
        raise PDBAbortExecution(summary.failed(True))


def verify_text_formatter(summary: Summary) -> None:
    """Print output text for the verify sub-command as simple text"""
    for entry in summary.files:
        if entry.get("status") == "fail":
            cli_out_write(f"{entry.get('path')}: {entry.get('error')}")

    cli_out_write(f"Number of files checked = {summary.success(True)}")
    cli_out_write(f"Number of files missing or different = {summary.failed(True)}")
    cli_out_write(f"Number of files present in destination only = {summary.skipped(True)}")

    if summary.failed(True):
        raise PDBAbortExecution(summary.failed(True))


@pdbstore_command(group="Administration")
def storage(
    parser: PDBStoreArgumentParser,  # pylint: disable=unused-argument
    *args: Any,  # pylint: disable=unused-argument
) -> Any:
    """
    Manage the storage backend holding a symbol store
    """


@pdbstore_subcommand(
    formatters={"text": migrate_text_formatter, "json": summary_json_formatter},
)
def storage_migrate(
    parser: PDBStoreArgumentParser,
    subparser: argparse.ArgumentParser,
    *args: Any,
) -> Any:
    """
    Copy a symbol store from one storage backend to another
    """
    subparser.add_argument(
        "--dry-run",
        dest="dry_run",
        default=False,
        action="store_true",
        help="Report what would be transferred without writing anything.",
    )

    subparser.add_argument(
        "-F",
        "--force",
        dest="overwrite",
        default=False,
        action="store_true",
        help="""Transfer files even when they are already present in the
        destination. Defaults to False, so an interrupted migration is resumed
        by running the same command again.""",
    )

    _add_common_arguments(subparser)

    opts = parser.parse_args(*args)
    source, destination = _blob_stores(opts)

    return MigrateStorageInteractor(source, destination).execute(
        opts.dry_run, opts.overwrite, opts.prefix or ""
    )


@pdbstore_subcommand(
    formatters={"text": verify_text_formatter, "json": summary_json_formatter},
)
def storage_verify(
    parser: PDBStoreArgumentParser,
    subparser: argparse.ArgumentParser,
    *args: Any,
) -> Any:
    """
    Check that a destination store holds everything the source does
    """
    subparser.add_argument(
        "--deep",
        dest="deep",
        default=False,
        action="store_true",
        help="""Compare the content of every file instead of its size only.
        Conclusive, but it transfers both stores in full.""",
    )

    _add_common_arguments(subparser)

    opts = parser.parse_args(*args)
    source, destination = _blob_stores(opts)

    return VerifyStorageInteractor(source, destination).execute(opts.prefix or "", opts.deep)


def _add_common_arguments(subparser: argparse.ArgumentParser) -> None:
    """Add the options both sub-commands share."""
    subparser.add_argument(
        "--prefix",
        metavar="KEY",
        dest="prefix",
        default=None,
        help="Restrict the operation to the files stored below KEY.",
    )

    add_storage_arguments(subparser, False)
    # The sub-parser already carries its own -h, so it must not be added twice.
    add_global_arguments(subparser, add_help=False, single=False)


def _blob_stores(opts: argparse.Namespace) -> Tuple[BlobStore, BlobStore]:
    """Resolve both store locations into the backends serving them.

    These sub-commands work one level below the rest of the command line: they
    copy and compare files without reading the transactions those files belong
    to. That is precisely what lets a store move between backends without any
    risk of its content being reinterpreted along the way.

    :param opts: The parsed command line.
    :return: The source and destination blob stores.
    :raise:
        :CommandLineError: A location is missing, or both name the same store.
        :PDBStoreException: A location uses an unsupported scheme.
    """
    source_location = opts.input_store_dir
    if not source_location:
        raise CommandLineError("no source symbol store given")

    destination_location = opts.store_dir
    if not destination_location:
        raise CommandLineError("no destination symbol store given")

    if str(source_location) == str(destination_location):
        raise CommandLineError("source and destination symbol stores are the same")

    return create_blob_store(source_location), create_blob_store(destination_location)

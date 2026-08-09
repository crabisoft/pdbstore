import argparse
import sys
import time
from pathlib import Path

from pdbstore import templates
from pdbstore.cli.args import add_global_arguments, add_storage_arguments
from pdbstore.cli.command import (
    pdbstore_command,
    pdbstore_subcommand,
    PDBStoreArgumentParser,
)
from pdbstore.exceptions import CommandLineError
from pdbstore.factory import open_store
from pdbstore.io.output import cli_out_write
from pdbstore.typing import Any, IO, Optional, TypedDict, Union
from pdbstore.usecases.report import GenerateReportInteractor
from pdbstore.usecases.statistics import Statistics


class StoreLocation:
    """What the report templates need to know about the analyzed store.

    Templates head their output with the store location. Passing this rather
    than the store itself keeps them working against a remote backend, where
    ``rootdir`` names a URI instead of a directory.
    """

    def __init__(self, location: str) -> None:
        self.rootdir: str = location

    def __str__(self) -> str:
        """Get the store location as a string."""
        return self.rootdir


class ReportDict(TypedDict):
    """Report Dictionary"""

    type: str
    start: float
    store: StoreLocation
    statistics: Statistics
    store_name: Optional[str]
    stream: Union[IO[Any], Path]


def report_text_formatter(report_dict: ReportDict) -> None:
    """Print output text for report command"""
    _report_render(report_dict, "text")


def report_json_formatter(report_dict: ReportDict) -> None:
    """Print output text from a Summary object as JSON format"""
    _report_render(report_dict, "json")


def report_markdown_formatter(report_dict: ReportDict) -> None:
    """Print output text from a Summary object as Markdown format"""
    _report_render(report_dict, "markdown")


def report_html_formatter(report_dict: ReportDict) -> None:
    """Print output text from a Summary object as HTML format"""
    _report_render(report_dict, "html")


@pdbstore_command(group="Analysis")
def report(
    parser: PDBStoreArgumentParser,  # pylint: disable=unused-argument
    *args: Any,  # pylint: disable=unused-argument
) -> Any:
    """
    Generate reports
    """


@pdbstore_subcommand(
    formatters={
        "text": report_text_formatter,
        "json": report_json_formatter,
        "markdown": report_markdown_formatter,
        "html": report_html_formatter,
    },
)
def report_product(
    parser: PDBStoreArgumentParser,
    subparser: argparse.ArgumentParser,
    *args: Any,
) -> Any:
    """
    Generate a report based on product name and version
    """
    return _report_command(GenerateReportInteractor.PRODUCTS, parser, subparser, *args)


@pdbstore_subcommand(
    formatters={
        "text": report_text_formatter,
        "json": report_json_formatter,
        "markdown": report_markdown_formatter,
        "html": report_html_formatter,
    },
)
def report_file(
    parser: PDBStoreArgumentParser,
    subparser: argparse.ArgumentParser,
    *args: Any,
) -> Any:
    """
    Generate a report based on files
    """
    return _report_command(GenerateReportInteractor.FILES, parser, subparser, *args)


@pdbstore_subcommand(
    formatters={
        "text": report_text_formatter,
        "json": report_json_formatter,
        "markdown": report_markdown_formatter,
        "html": report_html_formatter,
    },
)
def report_transaction(
    parser: PDBStoreArgumentParser,
    subparser: argparse.ArgumentParser,
    *args: Any,
) -> Any:
    """
    Generate a report based on transactions
    """
    return _report_command(GenerateReportInteractor.TRANSACTIONS, parser, subparser, *args)


def _report_command(
    report_type: str,
    parser: PDBStoreArgumentParser,
    subparser: argparse.ArgumentParser,
    *args: Any,
) -> Any:
    """
    Check if file(s) are indexed on the server
    """
    start_time = time.time()

    add_storage_arguments(subparser)
    subparser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        dest="output",
        required=False,
        default=sys.stdout,
        help="Generate PATH file. Defaults to stdout",
    )

    add_global_arguments(subparser, False)

    opts = parser.parse_args(*args)

    # Check input configuration and arguments
    store_dir = opts.store_dir
    if not store_dir:
        raise CommandLineError("no symbol store directory given")

    state = open_store(store_dir)

    generated = GenerateReportInteractor(state).execute(report_type)
    if generated is None:
        raise CommandLineError(f"failed to generate {report_type} report")

    if "store_id" in opts and opts.store_id:
        store_name = opts.store_id
    else:
        store_name = None

    report_dict: ReportDict = {
        "type": report_type,
        "start": start_time,
        "store": StoreLocation(state.gateway.location),
        "statistics": generated.statistics,
        "store_name": store_name or "",
        "stream": opts.output,
    }

    return report_dict


def _report_render(report_dict: ReportDict, report_format: str) -> None:
    # Generate the requested report
    rendered_text = templates.render_template(
        report_dict["type"],
        report_format,
        report_dict["start"],
        report=report_dict,
    )
    if report_dict.get("stream") is not sys.stdout:
        out_file: Path = Path(str(report_dict.get("stream"))).resolve()
        if out_file.is_file():
            out_file.unlink(missing_ok=True)
        else:
            out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(rendered_text, encoding="utf-8")
    else:
        cli_out_write(rendered_text)

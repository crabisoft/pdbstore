import argparse
import os

from pdbstore.cli.command import BaseCommand
from pdbstore.cli.once_argument import OnceArgument
from pdbstore.const import ENV_PDBSTORE_STORAGE_DIR


def add_global_arguments(
    parser: argparse.ArgumentParser, add_help: bool = True
) -> None:
    """Add global parsers command-line options."""
    BaseCommand.init_config(parser)
    BaseCommand.init_log_file(parser)
    BaseCommand.init_log_levels(parser)

    if hasattr(parser, "_command"):
        getattr(parser, "_command").init_formatters(parser)
    if add_help:
        parser.add_argument(
            "-h",
            "--help",
            dest="help",
            action="store_true",
            default=False,
            help="show this help message and exit",
        )


def add_storage_arguments(parser: argparse.ArgumentParser) -> None:
    """Add storage command-line options"""
    parser.add_argument(
        "-s",
        "--store-dir",
        metavar="DIRECTORY",
        dest="store_dir",
        type=str,
        help=(
            "Local root directory for the symbol store. "
            f"[env var: {ENV_PDBSTORE_STORAGE_DIR}]"
        ),
        required=False,
        default=os.getenv(ENV_PDBSTORE_STORAGE_DIR),
        action=OnceArgument,
    )


def add_product_arguments(parser: argparse.ArgumentParser) -> None:
    """Add product information command-line options"""
    parser.add_argument(
        "-p",
        "--product-name",
        metavar="PRODUCT",
        dest="product_name",
        type=str,
        help="Name of the product.",
        action=OnceArgument,
    )

    parser.add_argument(
        "-v",
        "--product-version",
        metavar="VERSION",
        dest="product_version",
        type=str,
        help="Version of the product.",
        action=OnceArgument,
    )

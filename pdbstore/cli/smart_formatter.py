import argparse
import textwrap


class SmartFormatter(argparse.HelpFormatter):
    """Text formatter for PDBStore commands"""

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        text = textwrap.dedent(text)
        return "".join(indent + line for line in text.splitlines(True))

import json

from pdbstore.exceptions import PDBAbortExecution
from pdbstore.io.output import cli_out_write
from pdbstore.store import Summary, TransactionType
from pdbstore.typing import Any, Optional


def default_json_formatter(data: Any) -> None:
    """Default JSON formatter"""
    data_json = json.dumps(data, indent=4)
    cli_out_write(data_json)


def summary_json_formatter(summary: Summary) -> None:
    """Print output text from a Summary object as JSON format"""
    out = []
    head: Optional[Summary] = summary
    while head:
        dct = {
            "id": head.transaction_id,
            "type": head.transaction_type.value if head.transaction_type else "undefined",
            "status": head.status.value,
            "success": head.success(summary.transaction_type != TransactionType.ADD),
            "failure": head.failed(True),
            "skip": head.skipped(True),
            "files": head.files,
            "message": head.error_msg,
        }
        out.append(dct)
        head = head.linked

    cli_out_write(json.dumps(out, indent=4))
    if summary.failed(True):
        raise PDBAbortExecution(summary.failed(True))

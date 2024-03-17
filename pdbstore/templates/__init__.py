"""The subpackage containing the builtin templates."""

import pkgutil
import time
from datetime import datetime

from jinja2 import Template

import pdbstore
from pdbstore.io.output import PDBStoreOutput
from pdbstore.typing import Any, Optional, Union


def get_template(report_type: str, output_format: str) -> Union[Template, None]:
    """Get a builtin template.
    :param report_type: The report type
    :param output_format: The targeted output format
    :return:
        A Jinja template object.
    """
    template_data = pkgutil.get_data(__name__, output_format + "/" + report_type + ".tmpl")
    if template_data is None:
        return None
    return Template(template_data.decode("utf-8"))


def render_template(
    report_type: str,
    output_format: str,
    time_start: Optional[float] = None,
    **kwargs: Any,
) -> Any:
    """Render a template given Template object.
    :param report_type: The report type
    :param output_format: The targeted output format
    :param time_start: Optional timestamp defining the beginning of the
        report generation.
    :param kwarg: Optional dictionary of named arguments to be
        transmitted to the Jinja when rendering the requested template.
    :return:
        The rendered template if successful, else an empty string.
    """
    template = get_template(report_type, output_format)
    if template is None:
        PDBStoreOutput().error(f"{output_format}/{report_type}.tmpl template not found")
        return ""

    now = datetime.today()

    kwargs["report"].update(
        {
            "now": now.strftime("%B %d, %Y at %H:%M:%S"),
            "__version__": pdbstore.__version__,
        }
    )

    def _generation_time(simple: Optional[bool] = True) -> Any:
        if not time_start:
            return "" if simple else 0
        elasped_time = time.time() - time_start
        if not simple:
            return elasped_time
        # hours
        hours = elasped_time // 3600
        # remaining seconds
        elasped_time = elasped_time - (hours * 3600)
        # minutes
        minutes = elasped_time // 60
        # remaining seconds
        seconds = elasped_time - (minutes * 60)
        text_repr = " in "
        if hours > 0:
            text_repr = f"{hours:02d}h"
        if minutes > 0:
            text_repr += f"{minutes:02d}m"
        text_repr += f"{seconds:02.2f}s"
        return text_repr

    template.globals["generation_time"] = _generation_time

    output = template.render(**kwargs)
    return output

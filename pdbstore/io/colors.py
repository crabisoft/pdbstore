import os

import colorama

from pdbstore import const
from pdbstore.typing import Any


def is_terminal(stream: Any) -> bool:
    """Determine whether a stream is interactive or not.

    :return: True if ``stream`` interactive else False
    """
    return hasattr(stream, "isatty") and stream.isatty()


def color_enabled(stream: object) -> bool:
    """Determine whether a stream  can support colorred output.

    This function follows https://bixense.com/clicolors convention, so you can
    define one of the following variable to enforce a mode, else the function
    will just check if `stream` is interactive or not:
    * :const:`~pdbstore.const.ENV_NO_COLOR`: No colors by just testing its existance
    * :const:`~pdbstore.const.ENV_CLICOLOR_FORCE`: Force color if defined and
      value is not **0**

    :param stream: The stream to be tested.

    :return: True if colorred output is enabled, else False
    """

    if os.getenv(const.ENV_NO_COLOR, "0") != "0":
        # CLICOLOR_FORCE != 0, ANSI colors should be enabled no matter what.
        return True

    if os.getenv(const.ENV_CLICOLOR_FORCE) is not None:
        # Enable fully colorred mode
        return True

    return is_terminal(stream)


def init_colorama(stream: object) -> None:
    """Initialize colorama.
    :param stream: The stream to be used to determine if colorred mode is supported not
    """
    if color_enabled(stream):
        if os.getenv(const.ENV_CLICOLOR_FORCE, "0") != "0":
            # Otherwise it is not really forced if colorama doesn't feel it
            colorama.init(strip=False, convert=False)
        else:
            colorama.init()

""" pdbstore constants. """

from pdbstore import _version

__all__ = [
    "ADMIN_DIRNAME",
    "HISTORY_FILENAME",
    "LASTID_FILENAME",
    "PINGME_FILENAME",
    "SERVER_FILENAME",
    "USER_AGENT",
    "ENV_PDBSTORE_CFG",
    "ENV_PDBSTORE_STORAGE_DIR",
    "ENV_PDBSTORE_VERBOSE",
    "ENV_PDBSTORE_COLOR_DARK",
]

#
# Predefined directory/file names
#

ADMIN_DIRNAME = "000Admin"
"""Predefined directory for symbol store administration """

HISTORY_FILENAME = "history.txt"
"""The symbol store history file name.

This file contains the full history, so
:const:`add <pdbstore.store.transaction_type.TransactionType.ADD>` and
:const:`del <pdbstore.store.transaction_type.TransactionType.DEL>`
transactions can be present
"""

LASTID_FILENAME = "lastid.txt"
"""The file containing the last transaction id """

PINGME_FILENAME = "pingme.txt"
"""The file defining the date/time of the latest modification """

SERVER_FILENAME = "server.txt"
"""The server symbol store file containing only
:const:`add <pdbstore.store.transaction_type.TransactionType.ADD>`
transactions history
"""

#
# HTTP/HTTPS requests
#

USER_AGENT = f"{_version.__title__}/{_version.__version__}"
"""Predefined user-agent for HTTP/HTTPS requests """

#
# Environment variable names
#

ENV_PDBSTORE_CFG = "PDBSTORE_CFG"
"""Define list of configuration files

It can be a path to a local configuration to be used to configure
**pdbstore** with appropriate default values
"""

ENV_PDBSTORE_STORAGE_DIR = "PDBSTORE_STORAGE_DIR"
"""Root directory for the symbol store

It can be a path to a local directory where all symbol store files will
be stored
"""

ENV_PDBSTORE_VERBOSE = "PDBSTORE_VERBOSE"
"""Indicate if verbose output is required

When set to 1, **pdbstore** will also print debug messages, else only
info, warning and error messages are print.
"""

ENV_PDBSTORE_URL = "PDBSTORE_URL"
"""Remote symbol server url

The url must be defined with protocol and server name only.
Ex.: https://myserver.net
"""

ENV_PDBSTORE_SSL_VERIFY = "PDBSTORE_SSL_VERIFY"
"""Indicate if SSL certificates should be validated or not.

It can be one of the following values:

- 0 to disable the SSL certificates validation
- 1 to enable the SSL certificates validation
- Path to a local CA bundle file to properly validate SSL certificates
"""

ENV_PDBSTORE_TIMEOUT = "PDBSTORE_TIMEOUT"
"""Timeout value when performing HTTP/HTTPS requests to remote symbol server

It can be an integer defining the required timeout value in seconds.
"""

ENV_PDBSTORE_USER_AGENT = "PDBSTORE_USER_AGENT"
"""The user agent to send to remote symbol server with HTTP/HTTPS requests

It must be formatted with ``NAME/VERSION``, where:

- `NAME` must be a string defining the agent name
- `VERSION` must be a version (digit and dot) defining the agent version
"""

ENV_PDBSTORE_API_KEY = "PDBSTORE_API_KEY"
"""API key required for remote symbol server authentication with HTTP/HTTPS requests
"""

ENV_PDBSTORE_TEMP_DIR = "PDBSTORE_TEMP_DIR"
"""Use specific temporary directory

This environment variable must a full path. If not defined, default system
temporary directory will be use.
"""

ENV_NO_COLOR = "NO_COLOR"
""" Disable ANSI colors """

ENV_CLICOLOR_FORCE = "CLICOLOR_FORCE"
"""ANSI colors should be enabled.

Different from 0 to enforce ANSI colors
"""

ENV_PDBSTORE_COLOR_DARK = "PDBSTORE_COLOR_DARK"
"""Use dark ANSI color scheme.

It must be different from 0 to enforce dark colors
"""

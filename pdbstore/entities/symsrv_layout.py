"""Layout of a SymSrv-compatible symbol store.

This module is the single place where the on-store naming convention is
encoded. It computes *keys* only: it never touches a filesystem, a network or
any other external resource, which makes the layout identical whatever blob
store ends up holding the bytes. That property is what guarantees a store
written through any backend stays readable by ``symsrv.dll`` and Visual Studio.

A key is a ``/``-separated, store-relative string. Translating a key into a
concrete location is the responsibility of a
:class:`BlobStore <pdbstore.usecases.gateways.blob_store.BlobStore>`
implementation.
"""

from pdbstore import const
from pdbstore.typing import List

__all__ = [
    "KEY_SEPARATOR",
    "admin_key",
    "compressed_file_name",
    "deleted_marker_key",
    "entry_dir_key",
    "entry_file_name",
    "entry_key",
    "history_key",
    "join_key",
    "lastid_key",
    "pingme_key",
    "promoted_marker_key",
    "server_key",
    "split_key",
    "transaction_key",
]

KEY_SEPARATOR = "/"
"""The canonical separator used inside a store key."""


def join_key(*parts: str) -> str:
    """Assemble a store key from its individual parts.

    :param parts: The key components, in order. Empty components are dropped.
    :return: The assembled key.
    """
    return KEY_SEPARATOR.join([part for part in parts if part])


def split_key(key: str) -> List[str]:
    """Split a store key into its individual parts.

    :param key: The key to split.
    :return: The list of key components.
    """
    return [part for part in key.split(KEY_SEPARATOR) if part]


def compressed_file_name(file_name: str) -> str:
    """Derive the name a file takes once compressed as a cab archive.

    The SymSrv convention replaces the last character of the name by an
    underscore, so ``foo.pdb`` is stored as ``foo.pd_``.

    :param file_name: The uncompressed file name.
    :return: The compressed file name.
    """
    return file_name[:-1] + "_"


def entry_file_name(file_name: str, compressed: bool) -> str:
    """Determine the name a transaction entry takes inside the store.

    :param file_name: The original file name.
    :param compressed: `True` when the file is stored as a cab archive.
    :return: The name used inside the store.
    """
    return compressed_file_name(file_name) if compressed else file_name


def entry_dir_key(file_name: str, file_hash: str) -> str:
    """Compute the key of the directory holding one transaction entry.

    :param file_name: The original file name.
    :param file_hash: The file signature.
    :return: The store key of the entry directory.
    """
    return join_key(file_name, file_hash)


def entry_key(file_name: str, file_hash: str, compressed: bool) -> str:
    """Compute the key under which a transaction entry is stored.

    :param file_name: The original file name.
    :param file_hash: The file signature.
    :param compressed: `True` when the file is stored as a cab archive.
    :return: The store key of the entry.
    """
    return join_key(file_name, file_hash, entry_file_name(file_name, compressed))


def admin_key() -> str:
    """Compute the key of the store administration directory.

    :return: The store key of the ``000Admin`` directory.
    """
    return const.ADMIN_DIRNAME


def transaction_key(transaction_id: str) -> str:
    """Compute the key of the file listing the entries of one transaction.

    :param transaction_id: The transaction identifier.
    :return: The store key of the transaction file.
    """
    return join_key(const.ADMIN_DIRNAME, transaction_id)


def deleted_marker_key(transaction_id: str) -> str:
    """Compute the key marking a transaction as deleted.

    :param transaction_id: The transaction identifier.
    :return: The store key of the ``.deleted`` marker.
    """
    return transaction_key(transaction_id) + ".deleted"


def promoted_marker_key(transaction_id: str) -> str:
    """Compute the key marking a transaction as promoted.

    :param transaction_id: The transaction identifier.
    :return: The store key of the ``.promoted`` marker.
    """
    return transaction_key(transaction_id) + ".promoted"


def server_key() -> str:
    """Compute the key of the server file.

    :return: The store key of ``000Admin/server.txt``.
    """
    return join_key(const.ADMIN_DIRNAME, const.SERVER_FILENAME)


def history_key() -> str:
    """Compute the key of the history file.

    :return: The store key of ``000Admin/history.txt``.
    """
    return join_key(const.ADMIN_DIRNAME, const.HISTORY_FILENAME)


def lastid_key() -> str:
    """Compute the key of the file holding the last allocated transaction id.

    :return: The store key of ``000Admin/lastid.txt``.
    """
    return join_key(const.ADMIN_DIRNAME, const.LASTID_FILENAME)


def pingme_key() -> str:
    """Compute the key of the file stamping the last store modification.

    :return: The store key of ``pingme.txt``.
    """
    return const.PINGME_FILENAME

"""Storage administration interactors.

The only interactors allowed to depend on
:class:`BlobStore <pdbstore.usecases.gateways.blob_store.BlobStore>` directly.
Moving a store between backends is expressed in keys, not in transactions, so
here the blob store *is* the subject matter rather than an implementation
detail. The layering rules single this package out for that reason.
"""

from pdbstore.usecases.storage.migrate import MigrateStorageInteractor, transfer_blob
from pdbstore.usecases.storage.verify import VerifyStorageInteractor

__all__ = [
    "MigrateStorageInteractor",
    "VerifyStorageInteractor",
    "transfer_blob",
]

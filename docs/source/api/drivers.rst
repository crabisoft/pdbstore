drivers package
===============

.. automodule:: pdbstore.drivers

The outermost layer, holding everything that talks to something concrete: a
filesystem, an object store, a compression utility. Adding a storage backend
means implementing the blob store gateway here and registering its URI scheme;
nothing above this package has to change.

.. toctree::
   :caption: drivers package
   :maxdepth: 1
   :hidden:

   drivers/blob
   drivers/compression
   drivers/parsing

- :doc:`blob package <drivers/blob>`
- :doc:`compression package <drivers/compression>`
- :doc:`parsing package <drivers/parsing>`

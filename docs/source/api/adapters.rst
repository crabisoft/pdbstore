adapters package
================

.. automodule:: pdbstore.adapters

Converts between the shape the interactors work with and the shape the outside
world expects. The SymSrv adapter is the single place where the on-store format
is turned into bytes, which is what makes that format identical whatever
backend ends up holding it.

.. toctree::
   :caption: adapters package
   :maxdepth: 1
   :hidden:

   adapters/symsrv

- :doc:`symsrv package <adapters/symsrv>`

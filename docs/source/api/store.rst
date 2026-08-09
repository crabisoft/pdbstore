store package
=============

.. deprecated:: 1.2

   This package is kept for backwards compatibility. A symbol store is now
   described by the :doc:`entities package <entities>`, driven by the
   interactors of the :doc:`usecases package <usecases>` and reached through
   their gateways.

   The classes below keep the previous API working by assembling that graph and
   delegating to it. Their path-shaped members, such as ``Store.rootdir`` or
   ``TransactionEntry.stored_path``, only apply to a store held on a local
   filesystem; new code should use :func:`pdbstore.factory.open_store` instead.

.. toctree::
   :caption: store package
   :maxdepth: 1
   :hidden:

   store/store
   store/history
   store/transactions
   store/transaction
   store/transaction_type
   store/entry
   store/summary

- :doc:`store module <store/store>`
- :doc:`history module <store/history>`
- :doc:`transactions module <store/transactions>`
- :doc:`transaction module <store/transaction>`
- :doc:`transaction_type module <store/transaction_type>`
- :doc:`entry module <store/entry>`
- :doc:`summary module <store/summary>`

entities package
================

.. automodule:: pdbstore.entities

The innermost layer, describing what a symbol store is made of. None of these
objects performs any input/output: reaching an actual store is done through the
gateways of the :doc:`usecases package <usecases>`.

.. toctree::
   :caption: entities package
   :maxdepth: 1
   :hidden:

   entities/transaction
   entities/entry
   entities/summary
   entities/symsrv_layout
   entities/transaction_type

- :doc:`transaction module <entities/transaction>`
- :doc:`entry module <entities/entry>`
- :doc:`summary module <entities/summary>`
- :doc:`symsrv_layout module <entities/symsrv_layout>`
- :doc:`transaction_type module <entities/transaction_type>`

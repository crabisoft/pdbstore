usecases package
================

.. automodule:: pdbstore.usecases

One interactor per operation of the symbol store, written in terms of
:doc:`entities <entities>` and gateways only. The gateways declare what an
interactor needs from the outside world; they are implemented by the
:doc:`adapters <adapters>` and :doc:`drivers <drivers>` packages.

.. toctree::
   :caption: usecases package
   :maxdepth: 1
   :hidden:

   usecases/gateways
   usecases/interactors
   usecases/storage
   usecases/store_state

- :doc:`gateways package <usecases/gateways>`
- :doc:`interactors <usecases/interactors>`
- :doc:`storage package <usecases/storage>`
- :doc:`store_state module <usecases/store_state>`

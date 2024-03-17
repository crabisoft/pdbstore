CLI reference
=============

This section describe the Conan built-in commands, like ``pdbstore add`` or ``pdbstore del``.

**Storage commands:**

.. toctree::
   :caption: Consumer commands
   :maxdepth: 1
   :hidden:

   commands/add
   commands/clean
   commands/del
   commands/fetch
   commands/query
   commands/promote
   commands/report
   commands/unused

- :doc:`pdbstore add <commands/add>`: Add files to local symbol store
- :doc:`pdbstore clean <commands/clean>`: Remove old transactions associated given some criteria
- :doc:`pdbstore del <commands/del>`: Delete transaction from local symbol store
- :doc:`pdbstore fetch <commands/fetch>`: Fetch symbol files from for a local symbol store
- :doc:`pdbstore query <commands/query>`: Check if file(s) are indexed from local symbol store
- :doc:`pdbstore promote <commands/promote>`: Promote one transaction from one symbol store to another one
- :doc:`pdbstore report <commands/report>`: Generate report for a local symbol store
- :doc:`pdbstore unused <commands/unused>`: Find all files not used since a specific date

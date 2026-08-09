.. _commands_storage:

pdbstore storage
================

.. code-block:: text

    $ pdbstore storage -h
    usage: pdbstore storage {migrate,verify} ...

    Manage the storage backend holding a symbol store

    positional arguments:
      {migrate,verify}
        migrate             Copy a symbol store from one storage backend to another
        verify              Check that a destination store holds everything the
                            source does

The ``pdbstore storage`` requires an sub-command name to indicate the operation
to be performed on the storage backend itself:

* `migrate` : copy a symbol store from one storage backend to another one
* `verify` : check that a destination store holds everything the source does

Both sub-commands work on the stored files rather than on the transactions those
files belong to. A migration therefore never re-interprets the store it copies:
the destination is a byte for byte reproduction of the source, and remains
readable by ``symsrv.dll`` and Visual Studio.

Use the ``-i/--input-store-dir`` option to designate the source store, and the
``-s/--store-dir`` option to designate the destination store. Each of them can be
a local directory or a URI, so both ends may use a different backend. See
:ref:`cli_storage_backends` for the list of supported locations.

migrate
-------

.. code-block:: text

    $ pdbstore storage migrate -h
    usage: pdbstore storage migrate [-h] [--dry-run] [-F] [--prefix KEY]
                                    [-s LOCATION] [-i LOCATION] [-C PATH]
                                    [-S NAME] [-I NAME] [-L PATH] [-V [LEVEL]]
                                    [-f NAME]

    Copy a symbol store from one storage backend to another

    options:
      -h, --help            show this help message and exit
      --dry-run             Report what would be transferred without writing
                            anything.
      -F, --force           Transfer files even when they are already present in
                            the destination. Defaults to False, so an interrupted
                            migration is resumed by running the same command
                            again.
      --prefix KEY          Restrict the operation to the files stored below KEY.
      -s LOCATION, --store-dir LOCATION
                            Root directory of the output symbol store, or a URI
                            such as s3://bucket/prefix. [env var:
                            PDBSTORE_STORAGE_DIR]
      -i LOCATION, --input-store-dir LOCATION
                            Root directory of the input symbol store, or a URI
                            such as s3://bucket/prefix.
      -C PATH, --config-file PATH
                            Configuration file to use. Can be used multiple times.
                            [env var: PDBSTORE_CFG]
      -S NAME, --store NAME Which configuration section should be used. If not
                            defined, the default will be used
      -I NAME, --input-store NAME
                            Which configuration section should be used as input
                            store.
      -L PATH, --log-file PATH
                            Send output to PATH instead of stderr.
      -V [LEVEL], --verbosity [LEVEL]
                            Level of detail of the output. Valid options from less
                            verbose to more verbose: -Vquiet, -Verror, -Vwarning,
                            -Vnotice, -Vstatus, -V or -Vverbose, -VV or -Vdebug,
                            -VVV or -vtrace
      -f NAME, --format NAME
                            Select the output format: json

The ``pdbstore storage migrate`` command copies every file of the source store
into the destination store:

.. code-block:: console

   $ pdbstore storage migrate -i /some/where/release -s s3://mybucket/release

Files already present in the destination are skipped, so an interrupted
migration is resumed by simply running the same command again. Use the
``-F/--force`` command-line option to transfer them anyway, for example to
repair a destination whose content is known to be damaged.

Use the ``--dry-run`` command-line option to report the files that would be
transferred without writing anything to the destination.

Use the ``--prefix`` command-line option to restrict the operation to a part of
the store. ``--prefix 000Admin`` transfers the transaction bookkeeping only,
whereas ``--prefix mylib.pdb`` transfers every signature of a single symbol
file.

verify
------

.. code-block:: text

    $ pdbstore storage verify -h
    usage: pdbstore storage verify [-h] [--deep] [--prefix KEY] [-s LOCATION]
                                   [-i LOCATION] [-C PATH] [-S NAME] [-I NAME]
                                   [-L PATH] [-V [LEVEL]] [-f NAME]

    Check that a destination store holds everything the source does

    options:
      -h, --help            show this help message and exit
      --deep                Compare the content of every file instead of its size
                            only. Conclusive, but it transfers both stores in
                            full.
      --prefix KEY          Restrict the operation to the files stored below KEY.
      -s LOCATION, --store-dir LOCATION
                            Root directory of the output symbol store, or a URI
                            such as s3://bucket/prefix. [env var:
                            PDBSTORE_STORAGE_DIR]
      -i LOCATION, --input-store-dir LOCATION
                            Root directory of the input symbol store, or a URI
                            such as s3://bucket/prefix.
      -C PATH, --config-file PATH
                            Configuration file to use. Can be used multiple times.
                            [env var: PDBSTORE_CFG]
      -S NAME, --store NAME Which configuration section should be used. If not
                            defined, the default will be used
      -I NAME, --input-store NAME
                            Which configuration section should be used as input
                            store.
      -L PATH, --log-file PATH
                            Send output to PATH instead of stderr.
      -V [LEVEL], --verbosity [LEVEL]
                            Level of detail of the output. Valid options from less
                            verbose to more verbose: -Vquiet, -Verror, -Vwarning,
                            -Vnotice, -Vstatus, -V or -Vverbose, -VV or -Vdebug,
                            -VVV or -vtrace
      -f NAME, --format NAME
                            Select the output format: json

The ``pdbstore storage verify`` command compares both stores file by file, and
reports the files that are missing from the destination or that differ from the
source:

.. code-block:: console

   $ pdbstore storage verify -i /some/where/release -s s3://mybucket/release

Run it before decommissioning the source store: a migration that reported no
error is not by itself a proof that everything made it across.

By default, two files are considered identical when they have the same size.
Use the ``--deep`` command-line option to compare their content instead. This
is conclusive, but it transfers both stores in full.

Files that exist in the destination only are reported but are not considered an
error, since a destination store may legitimately hold more than the source.

The command exits with a non-zero status as soon as one file is missing or
differs, so that it can gate an automated migration.

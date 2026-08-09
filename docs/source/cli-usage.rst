############################
Getting started with the CLI
############################

``pdbstore`` provides a :command:`pdbstore` command-line tool to interact
with local symbol store. It uses a configuration file to define the default
symbol store properties.

.. _cli_configuration:

Configuration
=============

Files
-----

``pdbstore`` looks up 3 configuration files by default:

``PDBSTORE_CFG`` environment variable
    An environment variable that contains the path to a configuration file

``/etc/pdbstore.cfg``
    System-wide configuration file

``~/.pdbstore.cfg``
    User configuration file

You can use a different configuration file with the ``--config-file`` option.

Content
-------

The configuration file uses the ``INI`` format. It contains at least a
``[global]`` section. , and a specific section for each symbol server.
For example:

.. code-block:: ini

   [global]
   default = release
   keep = 90

   [release]
   store = /some/where/release
   keep = 1

   [snapshot]
   store = /some/where/snapshot
   keep = 10

   [oneproduct]
   store = /some/where/release
   product = oneproduct
   
The ``default`` option of the ``[global]`` section defines the symbol store to
use if no store is explicitly specified with the ``--store-id`` CLI option.

The ``[global]`` section also defines the values for the default storage
parameters. You can override the values in each symbol store section.

.. list-table:: Global options
   :header-rows: 1

   * - Option
     - Possible values
     - Description
   * - ``store``
     - ``str``
     - The default store name.
   * - ``keep``
     - Integer
     - The maximum number of transactions to keep for the same product name and version.
       It can be 0 to keep all existing transactions.

.. list-table:: Symbol store/server options
   :header-rows: 1

   * - Option
     - Possible values
     - Description
   * - ``store``
     - ``str``
     - Location of the symbol store. It can be a local root directory, or a URI
       naming another storage backend. See :ref:`cli_storage_backends`.
   * - ``product``
     - ``str``
     - Name of the product.
   * - ``version``
     - ``str``
     - Version of the product.

A ``store`` name must defined for each symbol store section with unique name.

.. _cli_storage_backends:

Storage backends
================

A symbol store is designated by a location, either through the ``store`` option
of a configuration file, or through the ``-s/--store-dir`` command-line option.
That location can name any of the supported backends:

.. list-table:: Store locations
   :header-rows: 1

   * - Location
     - Description
   * - ``/some/where/release``
     - A local directory. This is the default when the location has no scheme.
   * - ``file:///some/where/release``
     - The same local directory, written as a URI.
   * - ``s3://mybucket/release``
     - An Amazon S3 bucket, optionally with a key prefix so that a single
       bucket can host several stores.

Whichever backend is used, the store keeps the very same layout, so it stays
readable by ``symsrv.dll`` and Visual Studio. A store can therefore be moved
from one backend to another with the :ref:`pdbstore storage migrate
<commands_storage>` command without any of its content being re-interpreted.

Amazon S3
---------

The S3 backend requires the ``boto3`` package, which is not installed by
default:

.. code-block:: console

   $ pip install --upgrade "pdbstore[s3]"

Credentials are resolved through the standard AWS chain, so the usual
``AWS_*`` environment variables, shared configuration files and instance roles
all apply. The following environment variables cover what that chain cannot
express:

.. list-table:: S3 environment variables
   :header-rows: 1

   * - Variable
     - Description
   * - ``PDBSTORE_S3_ENDPOINT_URL``
     - Endpoint of the object store. Only needed when the target is not AWS
       itself, such as MinIO or Ceph.
   * - ``PDBSTORE_S3_REGION``
     - Region of the bucket, overriding the one resolved from the AWS
       configuration.
   * - ``PDBSTORE_S3_PROFILE``
     - Named AWS profile to authenticate with.

Two behaviours differ from a store held on a local filesystem, and are worth
knowing before moving a store to a bucket:

Concurrent writes
   An object store has no atomic append, so publishing a transaction reads the
   store bookkeeping, extends it and writes it back. That sequence is guarded
   by a conditional write and retried on conflict, so two builds publishing at
   the same moment cannot overwrite one another. This requires a bucket that
   supports conditional requests, which AWS S3 does.

Unused files
   S3 reports when an object was last written, never when it was last read. The
   :ref:`pdbstore unused <commands_unused>` command therefore reports on the
   date a symbol was published rather than on the date it was last downloaded.
   Since a symbol file is written once and never modified, this amounts to the
   age of the symbol.

CLI
===

Output
------

The CLI also sends all the information, warning, and error messages to stderr, while keeping the final result in stdout, allowing multiple output formats like --format=html or --format=json and using redirects to create files --format=json > myfile.json. The information provided by the CLI will be more structured and thorough so that it can be used more easily for automation, especially in Web-Server or CI/CD systems.


Actions
-------

The ``pdbstore`` command expects at least one mandatory argument. This
argument is the action that you want to perform. For example:

.. code-block:: console

   $ pdbstore add -p myproduct -v 1.0 test.dll
   $ pdbstore del 92
   $ pdbstore query test.dll

Use the ``--help`` option to list the available action names:

.. code-block:: console

   $ pdbstore --help

Some actions require additional parameters. Use the ``--help`` option to
list mandatory and optional arguments for an action:

.. code-block:: console

   $ pdbstore add --help
   $ pdbstore query --help

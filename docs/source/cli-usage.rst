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
     - Local root directory for the symbol store.
   * - ``product``
     - ``str``
     - Name of the product.
   * - ``version``
     - ``str``
     - Version of the product.

A ``store`` name must defined for each symbol store section with unique name.

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

   $ pdbstore add -f test.dll -t myproduct -v 1.0
   $ pdbstore del -i 0000000092
   $ pdbstore query -f test.dll

Use the ``--help`` option to list the available action names:

.. code-block:: console

   $ pdbstore --help

Some actions require additional parameters. Use the ``--help`` option to
list mandatory and optional arguments for an action:

.. code-block:: console

   $ pdbstore add --help
   $ pdbstore query --help

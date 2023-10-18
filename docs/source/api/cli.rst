cli package
===========

cli module
----------

Cli class
^^^^^^^^^
.. autoclass:: pdbstore.cli.cli.Cli
    :members:
    :undoc-members:
    :show-inheritance:

Functions
^^^^^^^^^
.. automodule:: pdbstore.cli.cli
    :members: main
    :exclude-members: Cli

command module
--------------

BaseCommand
^^^^^^^^^^^
.. autoclass:: pdbstore.cli.command.BaseCommand
    :members:
    :undoc-members:
    :show-inheritance:

PDBStoreCommand
^^^^^^^^^^^^^^^
.. autoclass:: pdbstore.cli.command.PDBStoreCommand
    :members:
    :undoc-members:
    :show-inheritance:

PDBStoreSubCommand
^^^^^^^^^^^^^^^^^^
.. autoclass:: pdbstore.cli.command.PDBStoreSubCommand
    :members:
    :undoc-members:
    :show-inheritance:

PDBStoreArgumentParser
^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: pdbstore.cli.command.PDBStoreArgumentParser
    :members:
    :undoc-members:
    :show-inheritance:

Decorators
----------

pdbstore_command
^^^^^^^^^^^^^^^^

.. code-block:: text

    pdbstore_command(group, formatters = None)

Main decorator to declare a function as a new PDBStore command. Where the parameters are:

* `group` is the name of the group of commands declared under the same name. This grouping will appear executing the `pdbstore -h` command.
* `formatters` is a dict-like Python object where the `key` is the formatter name and the value is the function instance where will be processed the information returned by the command one.

.. code-block:: python
    :caption: example.py

    from pdbstore.cli.command import pdbstore_command, PDBStoreArgumentParser
    from pdbstore.io.output import PDBStoreOutput
    from pdbstore.typing import Any

    def output_json(msg: Any) -> None:
        return json.dumps({"results": msg)

    @pdbstore_command(group="My Group", formatters={"json": output_json)
    def example(parser: PDBStoreArgumentParser, *args: Any) -> Any:
        """
        Simple command example to print 'Hello World !!!' sentence
        """
        msg = "Hello World !!!"
        PDBStoreOutput().info(f"from example command: {msg}")
        return msg

.. important::

    The function decorated by ``@pdbstore_command(....)`` must have the same name as the Python file. For instance, the previous example, the file name is ``example.py``, and the command function decorated is ``def example(....)``.

pdbstore_subcommand
^^^^^^^^^^^^^^^^^^^

.. code-block:: text

    pdbstore_subcommand(formatters = None)

Similar to `pdbstore_command`, but this one is declaring a sub-command of an existing custom command. 

.. code-block:: python
    :caption: example.py

    import argparse
    from pdbstore.cli.command import pdbstore_command, pdbstore_subcommand, PDBStoreArgumentParser
    from pdbstore.io.output import PDBStoreOutput
    from pdbstore.typing import Any

    @pdbstore_subcommand()
    def example_bye(parser: PDBStoreArgumentParser, subparser: argparse.ArgumentParser, *args: Any) -> Any:
        """
        Simple sub-command example to print 'Bye bye bye' message to stderr
        """
        msg = "Bye bye bye"
        PDBStoreOutput().info(f"from example_bye sub-command: {msg}")

    @pdbstore_command(group="My Group")
    def example(parser: PDBStoreArgumentParser, *args: Any) -> Any:
        """
        Simple example command with sub-commands
        """


.. important::

    Notice that to declare a sub-command is required an empty Python function acts as the main command.
   
    The function decorated by ``@pdbstore_subcommand(....)`` must be prefixed by main command function name and the suffix, after ``_`` character, will be use as sub-command-name.

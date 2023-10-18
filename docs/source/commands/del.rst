.. _commands_del:

pdbstore del
============

.. code-block:: text

    $ pdbstore del -h
    usage: pdbstore del [-s DIRECTORY] [-V [LEVEL]] [-L PATH] [-C PATH] [-S NAME]
                        [-f NAME] [-h]
                        [ID ...]

    Delete files from local symbol store

    positional arguments:
      ID                    Transaction ID string.

    options:
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the symbol store. [env var:        
                            PDBSTORE_STORAGE_DIR]
      -V [LEVEL], --verbosity [LEVEL]
                            Level of detail of the output. Valid options from less      
                            verbose to more verbose: -Vquiet, -Verror, -Vwarning,       
                            -Vnotice, -Vstatus, -V or -Vverbose, -VV or -Vdebug, -VVV   
                            or -vtrace
      -L PATH, --log-file PATH
                            Send output to PATH instead of stderr.
      -C PATH, --config-file PATH
                            Configuration file to use. Can be used multiple times.      
                            [env var: PDBSTORE_CFG]
      -S NAME, --store NAME Which configuration section should be used. If not
                            defined, the default will be used
      -f NAME, --format NAME
                            Select the output format: text, json
      -h, --help            show this help message and exit


The ``pdbstore del`` will search for the speciifed transaction identifiers and delete
them from the specified if exists.

The ``pdbstore del`` will perform the requested delete operation with using transaction
identifier as unique criteria. If you want to delete transactions given more criteria,
please refer to :ref:`commands_clean` command

The ``pdbstore del`` command will:
- search for Portable Executable (**PE**) and **PDB** files if input directory is given
- check all input files to detect **PE** and **PDB** files
- extract **GUID** and **age** from required files
- add files that are not referenced yet based on their **GUID** and **age**
- delete oldest transactions if required
- print a summary to **stdout** stream
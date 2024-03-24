.. _commands_del:

pdbstore del
============

.. code-block:: text

    $ pdbstore del -h
    usage: pdbstore del [-s DIRECTORY] [--dry-run] [-V [LEVEL]] [-L PATH] [-C PATH] 
                        [-S NAME] [-f NAME] [-h] [ID ...]

    Delete files from local symbol store

    positional arguments:
      ID                    Transaction ID string.

    options:
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the symbol store. [env var:        
                            PDBSTORE_STORAGE_DIR]
      --dry-run             Do not delete file or directory, but show a list of paths 
                            to be removed.
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


The ``pdbstore del`` will search for the specified transaction identifiers and delete
all required associated files. A file will be automatically deleted if it is not referenced
anymore by the store.

The ``--dry-run`` option can be used to obtain a summary of files to be deleted along
the specified transaction.

The ``pdbstore del`` will perform the requested delete operation using transaction
identifier as unique criteria. If you want to delete transactions given more criteria,
please refer to :ref:`commands_clean` command

The ``pdbstore del`` command will:

* Search the requested transaction given by its identifier
* Collect all files that are referenced only by the transaction
* Remove all required files and empty directories

.. _commands_promote:

pdbstore promote
================

.. code-block:: text

    $ pdbstore promote -h
    usage: pdbstore promote [-c COMMENT] [-s DIRECTORY] [-i DIRECTORY] 
                            [-F] [-d] [-C PATH] [-S NAME] [-I NAME] 
                            [-L PATH] [-V [LEVEL]] [-f NAME] [-h] [ID ...]

    Find all files not used since a specific date

    positional arguments:
      ID                    Transaction ID string.

    options:
      -c COMMENT, --comment COMMENT
                            Comment for the transaction.
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the output symbol store. 
                            [env var: PDBSTORE_STORAGE_DIR]
      -i DIRECTORY, --input-store-dir DIRECTORY
                            Local root directory for the input symbol store.
      -F, --force           Overwrite any existing file from the store. uses file's    
                            hash to check if it's already exists in the store.
                            Defaults to False.
      -C PATH, --config-file PATH
                            Configuration file to use. Can be used multiple times.      
                            [env var: PDBSTORE_CFG]
      -S NAME, --store NAME Which configuration section should be used. If not
                            defined, the default will be used
      -I NAME, --input-store NAME Which configuration section should be used as
                            input store
      -L PATH, --log-file PATH
                            Send output to PATH instead of stderr.
      -V [LEVEL], --verbosity [LEVEL]
                            Level of detail of the output. Valid options from less      
                            verbose to more verbose: -Vquiet, -Verror, -Vwarning,       
                            -Vnotice, -Vstatus, -V or -Vverbose, -VV or -Vdebug, -VVV   
                            or -vtrace
      -f NAME, --format NAME
                            Select the output format: json
      -h, --help            show this help message and exit


The ``pdbstore promote`` command will search the specified transaction ID from the input
store and will automatically copy them into the output store by registering new transactions.

The command will do not perform any file type check since the input files are fetching
from an existing symbol store.

By default, ``pdbstore promote`` command will generate a default comment for the transaction
by using comment from specified transaction and appending `\ : Promote from <Input Symbol Store Path>`.
If a comment is specified through ``-c/--comment`` command-line option, the specified comment
will be used as it is.
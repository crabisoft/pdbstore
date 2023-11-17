.. _commands_query:

pdbstore query
==============

.. code-block:: text

    $ pdbstore query -h
    usage: pdbstore fetch [-s DIRECTORY] [-r] [-F] [-C PATH] [-S NAME] [-L PATH]
                          [-V [LEVEL]] [-f NAME] [-h] [FILE_OR_DIR ...]

    Check if file(s) are indexed on the server

    positional arguments:
      FILE_OR_DIR           Network path of files or directories to add. If the named   
                            file begins with an '@' symbol, it is treated as a
                            response file which is expected to contain a list of files  
                            (path and filename, 1 entry per line) to be stored.

    options:
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the symbol store. [env var:        
                            PDBSTORE_STORAGE_DIR]
      -r, --recursive       Add files or directories recursively.
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


The ``pdbstore query`` must be used to determine if a file is already indexed by a local
symbol store.
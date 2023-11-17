.. _commands_unused:

pdbstore unused
===============

.. code-block:: text

    $ pdbstore unused -h
    usage: pdbstore unused [-s DIRECTORY] [-C PATH] [-S NAME] [-L PATH] 
                           [-V [LEVEL]] [-f NAME] [-h] [DATE]

    Find all files not used since a specific date

    positional arguments:
      DATE                  Date given YYYY-MM-DD format.

    options:
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the symbol store. [env var:        
                            PDBSTORE_STORAGE_DIR]
      -C PATH, --config-file PATH
                            Configuration file to use. Can be used multiple times.      
                            [env var: PDBSTORE_CFG]
      -S NAME, --store NAME Which configuration section should be used. If not
                            defined, the default will be used
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


The ``pdbstore unused`` command will automatically determine all files that have not
been used since the specified date by comparing it to the most recent access time.

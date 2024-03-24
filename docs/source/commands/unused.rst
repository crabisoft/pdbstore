.. _commands_unused:

pdbstore unused
===============

.. code-block:: text

    $ pdbstore unused -h
    usage: pdbstore unused [-s DIRECTORY] [--date YY-MM-DDDD] [--days DAYS] [-d]
                           [-C PATH] [-S NAME] [-L PATH] [-V [LEVEL]] [-f NAME] [-h] 

    Find all files not used based on the last access time of the files.

    options:
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the symbol store. [env var:        
                            PDBSTORE_STORAGE_DIR]
      --date YY-MM-DDDD     Find all files that were last accessed before the 
                            specified date.
      --days DAYS           Find all files that were last accessed before today
                            minus the amount of days specified by 'DAYS'.
      -d --delete           Delete automatically all unused files
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


The ``pdbstore unused`` command will find all files not used since a specific date or
number of days based on their last access dates.
Optionally, ``--delete`` option can be used to delete automatically the files.

This command is particularly useful for removing old files from the downstream store
used by a symbol server, in order to conserve disk space.
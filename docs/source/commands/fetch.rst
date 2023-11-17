.. _commands_fetch:

pdbstore fetch
==============

.. code-block:: text

    $ pdbstore fetch -h
    usage: pdbstore fetch [-s DIRECTORY] [-r] [-O DIR] [-F] [-C PATH] [-S NAME] 
                          [-L PATH] [-V [LEVEL]] [-f NAME] [-h] [FILE_OR_DIR ...]

    Fetch all files from a symbol store

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
      -O DIR, --output DIR  Store requested files into DIR instead near from the
                            input file.
      -F, --full-name       Display file path without abbreviation.
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


The ``pdbstore fetch`` command will automatically determine all pdb files that are
currently available from local symbol store based on all executable, dynamic-link
library or Active-X controls given as input arguments.

You can decide to check for explicit files or also by exploring recursively a 
directory to find all available pdb files.

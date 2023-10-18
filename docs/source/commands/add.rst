.. _commands_add:

pdbstore add
============

.. code-block:: text

    $usage: pdbstore add [-p PRODUCT] [-v VERSION] [-c COMMENT] 
                    [-z | --compress | --no-compress] [-s DIRECTORY] [-k COUNT]
                    [-F] [-r] [-V [LEVEL]] [-L PATH] [-C PATH] [-S NAME] 
                    [-f NAME] [-h] [FILE_OR_DIR ...]

    Add files to local symbol store

    positional arguments:
      FILE_OR_DIR           Network path of files or directories to add. If the named  
                            file begins with an '@' symbol, it is treated as a
                            response file which is expected to contain a list of       
                            files (path and filename, 1 entry per line) to be stored.  

    options:
      -p PRODUCT, --product-name PRODUCT
                            Name of the product.
      -v VERSION, --product-version VERSION
                            Version of the product.
      -c COMMENT, --comment COMMENT
                            Comment for the transaction.
      -z, --compress, --no-compress
                            Store compressed files on the server. Defaults to False.   
                            (default: False)
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the symbol store. [env var:       
                            PDBSTORE_STORAGE_DIR]
      -k COUNT, --keep-count COUNT
                            The maximum number of transactions to preserve and once    
                            the number of transcations exceeds, older transactions     
                            are removed.
      -F, --force           Overwrite any existing file from the store. uses file's    
                            hash to check if it's already exists in the store.
                            Defaults to False.
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
      -S NAME, --store NAME
                            Which configuration section should be used. If not
                            defined, the default will be used
      -f NAME, --format NAME
                            Select the output format: text, json
      -h, --help            show this help message and exit

The ``pdbstore add`` command stores all supported binary files, based on command-line arguments, 
into the specified store.

The ``pdbstore add`` command will:
- search for Portable Executable (**PE**) and **PDB** files if input directory is given
- check all input files to detect **PE** and **PDB** files
- extract **GUID** and **age** from required files
- add files that are not referenced yet based on their **GUID** and **age**
- delete oldest transactions if required
- print a summary to **stdout** stream
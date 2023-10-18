.. _commands_clean:

pdbstore clean
==============

.. code-block:: text

    $ pdbstore clean -h
    usage: pdbstore clean [-s DIRECTORY] [-p PRODUCT] [-v VERSION] [-c COMMENT]
                          [-k KEEP_COUNT] [--dry-run] [-V [LEVEL]] [-L PATH] [-C PATH]  
                          [-S NAME] [-f NAME] [-h]

    Remove old transactions associated given some criteria

    options:
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the symbol store. [env var:        
                            PDBSTORE_STORAGE_DIR]
      -p PRODUCT, --product-name PRODUCT
                            Name of the product.
      -v VERSION, --product-version VERSION
                            Version of the product.
      -c COMMENT, --comment COMMENT
                            Comment to be search.
      -k KEEP_COUNT, --keep KEEP_COUNT
                            The maximum number of transactions to preserve and once     
                            the number" of transcations exceeds, older transactions     
                            are removed.
      --dry-run             Don't remove transactions/files from the symbol store.      
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


The ``pdbstore clean`` will search for all transactions where all criteria are matching
and delete them if `--dry-run` option is not used.

If you want to delete a transaction given by its identifier, please use :ref:`commands_del` command
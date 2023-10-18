.. _commands_report:

pdbstore report
===============

.. code-block:: text

    $ pdbstore report -h
    usage: pdbstore report {file,product,transaction} ...

    Generate reports

    positional arguments:
      {file,product,transaction}
        file                Generate a report based on files
        product             Generate a report based on product name and version
        transaction         Generate a report based on transactions

The ``pdbstore report`` requires an sub-command name to indicate the main target
of the report:

* `product` : report based on product name and version as primary classification keys
* `file` : report based on file name as primary classification key
* `transaction` : report based on transaction id as primary classification key

file report
-----------

.. code-block:: text

    $ pdbstore report file -h
    usage: pdbstore report file [-h] [-s DIRECTORY] [-o PATH] [-V [LEVEL]] [-L PATH]
                                [-C PATH] [-S NAME] [-f NAME]

    Generate a report based on files

    options:
      -h, --help            show this help message and exit
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the symbol store. [env var:        
                            PDBSTORE_STORAGE_DIR]
      -o PATH, --output PATH
                            Generate PATH file. Defaults to stdout
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
                            Select the output format: text, json, markdown, html        

product report
--------------

.. code-block:: text

    $ pdbstore report product -h
    usage: pdbstore report product [-h] [-s DIRECTORY] [-o PATH] [-V [LEVEL]]
                                  [-L PATH] [-C PATH] [-S NAME] [-f NAME]

    Generate a report based on product name and version

    options:
      -h, --help            show this help message and exit
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the symbol store. [env var:        
                            PDBSTORE_STORAGE_DIR]
      -o PATH, --output PATH
                            Generate PATH file. Defaults to stdout
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
                            Select the output format: text, json, markdown, html


transaction report
------------------

.. code-block:: text

    $ pdbstore report transaction -h
    usage: pdbstore report transaction [-h] [-s DIRECTORY] [-o PATH] [-V [LEVEL]]
                                      [-L PATH] [-C PATH] [-S NAME] [-f NAME]

    Generate a report based on transactions

    options:
      -h, --help            show this help message and exit
      -s DIRECTORY, --store-dir DIRECTORY
                            Local root directory for the symbol store. [env var:        
                            PDBSTORE_STORAGE_DIR]
      -o PATH, --output PATH
                            Generate PATH file. Defaults to stdout
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
                            Select the output format: text, json, markdown, html

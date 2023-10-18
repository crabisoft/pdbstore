# Exit codes for pdbstore command:
SUCCESS = 0  # 0: Success
ERROR_GENERAL = 1  # 1: General PDBStoreException error
USER_CTRL_C = 2  # 2: Ctrl+C
USER_CTRL_BREAK = 3  # 3: Ctrl+Break
ERROR_SIGTERM = 4  # 4: SIGTERM
ERROR_INVALID_CONFIGURATION = 5  # 5: Invalid configuration
ERROR_UNEXPECTED = 6  # 6: Unexpected error
ERROR_COMMAND_NAME = 7  # 7: Action/command name missing
ERROR_SUBCOMMAND_NAME = 8  # 8: Sub-command name missing
ERROR_ENCOUNTERED = 9  # 9: Error occurs during command execution

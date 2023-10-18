import sys

from pdbstore.cli import cli

if __name__ == "__main__":
    sys.exit(cli.main(sys.argv[1:]))

import argparse

from pdbstore.typing import Any, Optional, Sequence, Union


class OnceArgument(argparse.Action):
    """Allows declaring a parameter that can have only one value."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Union[str, Any, Sequence[Any], None],
        option_string: Optional[str] = None,
    ) -> None:
        if getattr(namespace, self.dest) is not None and self.default is None:
            msg = f"{option_string or 'undefined'} can only be specified once"
            raise argparse.ArgumentError(None, msg)
        setattr(namespace, self.dest, values)

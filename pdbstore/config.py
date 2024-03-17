import configparser
import os
from pathlib import Path

from pdbstore import const
from pdbstore.exceptions import ConfigDataError, ConfigIDError, ConfigMissingError
from pdbstore.typing import Any, Dict, List, Optional, PathLike

_DEFAULT_CONFIG_FILES: List[str] = [
    "/etc/pdbstore.cfg",
    str(Path.home() / ".pdbstore.cfg"),
]

_CONFIG_PARSER_ERRORS = (
    configparser.NoOptionError,
    configparser.NoSectionError,
)


def _resolve_file(filepath: PathLike) -> str:
    resolved = Path(filepath).resolve(strict=True)
    return str(resolved)


def _get_config_files(
    config_files: Optional[List[PathLike]] = None,
) -> List[str]:
    """
    Resolve path(s) to config files if they exist, with precedence:
    1. Files passed in config_files
    2. File defined in PDBSTORE_CFG
    3. User and system-wide config files
    :return: List of resolved to existing configuratio  file
    :raise:
        :ConfigMissingError: Unexpected error when resolving one of the
                             specified configuration file.
    """
    resolved_files: List[str] = []

    if config_files:
        for config_file in config_files:
            try:
                resolved = _resolve_file(config_file)
                resolved_files.append(resolved)
            except OSError as exo:
                raise ConfigMissingError(f"Cannot read config from file: {config_file}") from exo

        return resolved_files

    try:
        env_config = os.environ[const.ENV_PDBSTORE_CFG]
        resolved = _resolve_file(env_config)
        if resolved:
            return [resolved]
    except KeyError:
        pass
    except OSError as exo:
        raise ConfigMissingError(
            f"Cannot read config from {const.ENV_PDBSTORE_CFG}: {exo}"
        ) from exo

    for default_config_file in _DEFAULT_CONFIG_FILES:
        try:
            resolved = _resolve_file(default_config_file)
            resolved_files.append(resolved)
        except OSError:
            pass

    return resolved_files


class ConfigParser:  # pylint: disable=too-few-public-methods
    """A PDBStore configuration file representation."""

    def __init__(
        self,
        store_id: Optional[str] = None,
        config_files: Optional[List[PathLike]] = None,
    ) -> None:
        """Constructor.
        Load required configuration file and define `store_id` as
        default store.
        :param store_id: Optional default store name.
        :param config_files: Optional list of potential configuration files
        """
        self.store_id = store_id
        self.store_dir: Optional[str] = None
        self.keep_count: int = 0  # 0 means "keep all"
        self.compress: bool = False
        self.product_name: Optional[str] = None
        self.product_version: Optional[str] = None
        self._files = _get_config_files(config_files)
        if self._files:
            self._parse_config()

        elif self.store_id:
            raise ConfigMissingError(
                f"Symbol store id was provided ({self.store_id}) " "but no config file found"
            )

    def _parse_config(self) -> None:
        _config = configparser.ConfigParser()
        _config.read(self._files, encoding="utf-8")

        if self.store_id is None:
            try:
                self.store_id = _config.get("global", "default")
            except Exception as exg:
                raise ConfigIDError(
                    "Impossible to get the default symbol store id "
                    "(not specified in config file)"
                ) from exg

        if not _config.has_section(self.store_id):
            raise ConfigIDError(
                "Impossible to get symbol store details from " f"configuration ({self.store_id})"
            )

        if not _config.has_option(self.store_id, "store"):
            raise ConfigDataError(
                "Impossible to get symbol store directory from " f"configuration ({self.store_id})"
            )

        try:
            self.store_dir = _config.get(self.store_id, "store")
        except _CONFIG_PARSER_ERRORS:  # pragma: no cover
            pass

        try:
            self.keep_count = _config.getint("global", "keep")
        except ValueError as exv:
            # Value Error means the option exists but isn't an integer.
            raise ConfigDataError(
                "Invalid value detected for keep entry from global section (integer expected)"
            ) from exv
        except _CONFIG_PARSER_ERRORS:  # pragma: no cover
            pass
        try:
            self.keep_count = _config.getint(self.store_id, "keep")
        except ValueError as exv:
            # Value Error means the option exists but isn't an integer.
            raise ConfigDataError(
                "Invalid value detected for keep entry from "
                f"{self.store_id} section (integer expected)"
            ) from exv
        except _CONFIG_PARSER_ERRORS:  # pragma: no cover
            pass

        try:
            self.keep_count = _config.getboolean("global", "compress")
        except ValueError as exv:
            # Value Error means the option exists but isn't an integer.
            raise ConfigDataError(
                "Invalid value detected for compress entry from "
                "global section (boolean expected)"
            ) from exv
        except _CONFIG_PARSER_ERRORS:  # pragma: no cover
            pass
        try:
            self.keep_count = _config.getboolean(self.store_id, "compress")
        except ValueError as exv:
            # Value Error means the option exists but isn't an integer.
            raise ConfigDataError(
                "Invalid value detected for compress entry from "
                f"{self.store_id} section (boolean expected)"
            ) from exv
        except _CONFIG_PARSER_ERRORS:  # pragma: no cover
            pass

        try:
            self.product_name = _config.get(self.store_id, "product")
        except _CONFIG_PARSER_ERRORS:  # pragma: no cover
            pass

        try:
            self.product_version = _config.get(self.store_id, "version")
        except _CONFIG_PARSER_ERRORS:  # pragma: no cover
            pass

    def merge(self, config: Dict[str, Any]) -> "ConfigParser":
        """Merge current configuration with input commandline arguments"""
        for item in (
            "store_dir",
            "keep_count",
            "compress",
            "product_name",
            "product_version",
        ):
            value = config.get(item)
            if value is not None:
                setattr(self, item, value)
        return self

    def get_store_directory(self, name: str) -> Optional[str]:
        """Retrieve store directory path given by its name"""
        if not self._files:
            return None

        _config = configparser.ConfigParser()
        _config.read(self._files, encoding="utf-8")

        if not _config.has_section(name):
            raise ConfigIDError(
                f"Impossible to get symbol store details from configuration ({name})"
                + str(_config.sections())
            )

        if not _config.has_option(name, "store"):
            raise ConfigDataError(
                "Impossible to get symbol store directory from " f"configuration ({name})"
            )

        try:
            store_dir = _config.get(name, "store")
        except _CONFIG_PARSER_ERRORS:  # pragma: no cover
            store_dir = None
        return store_dir

"""
This module contains helper functions for locating and loading config
files.

The result of loading a config file are the "local" variables,
including the modules loaded via "import".
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .colors import *
from .util import *

__all__ = [
    "DEFAULT_LOCATIONS", "DEFAULT_CONFIG_FILE",
    "ConfigurationException", "Config",
]
logger = logging.getLogger(__name__)

DEFAULT_LOCATIONS = [
    Path("~/.config/evering/config.py"),
    Path("~/.evering/config.py"),
    Path("~/.evering.py"),
]

DEFAULT_CONFIG_FILE = """
known_files = "known_files"
config_dir = "config/"
binary = True
statement_prefix = "#"
expression_delimiters = ("{{", "}}")
"""

class ConfigurationException(Exception):
    pass

class Config:
    @classmethod
    def load_config_file(cls, path: Optional[Path]) -> "Config":
        """
        May raise: ConfigurationException
        """

        local_vars: Dict[str, Any]

        if path is None:
            # Try out all default config file locations
            for path in DEFAULT_LOCATIONS:
                try:
                    local_vars = cls._load_config_file(path)
                    break
                except (ReadFileException, ExecuteException) as e:
                    logger.debug(f"Could not load config from {style_path(path)}: {e}")
            else:
                raise ConfigurationException(style_error(
                    "No valid config file found in any of the default locations"))
        else:
            # Use the path
            try:
                local_vars = cls._load_config_file(path)
            except (ReadFileException, ExecuteException) as e:
                raise ConfigurationException(
                    style_error("Could not load config file from ") +
                    style_path(path) + f": {e}")

        return cls(local_vars)

    @staticmethod
    def _load_config_file(path: Path) -> Dict[str, Any]:
        """
        May raise: ReadFileException, ExecuteException
        """

        local_vars: Dict[str, Any] = {}
        safer_exec(DEFAULT_CONFIG_FILE, local_vars)

        safer_exec(read_file(path), local_vars)
        if not "base_dir" in local_vars:
            local_vars["base_dir"] = path.parent

        logger.info(f"Loaded config from {style_path(str(path))}")

        return local_vars

    def __init__(self, local_vars: Dict[str, Any]) -> None:
        """
        May raise: ConfigurationException
        """

        self.local_vars = local_vars

    def copy(self) -> "Config":
        return Config(copy_local_variables(self.local_vars))

    def _get(self, name: str, *types: type) -> Any:
        """
        May raise: ConfigurationException
        """

        if not name in self.local_vars:
            raise ConfigurationException(
                style_error(f"Expected a variable named ") +
                style_var(name))

        value = self.local_vars[name]

        if types:
            if not any(isinstance(value, t) for t in types):
                raise ConfigurationException(
                    style_error("Expexted variable ") + style_var(name) +
                    style_error(" to have one of the following types:\n" +
                                ", ".join(t.__name__ for t in types))
                )

        return value

    def _get_optional(self, name: str, *types: type) -> Optional[Any]:
        if not name in self.local_vars:
            return None
        else:
            return self._get(name, *types)

    def _set(self, name: str, value: Any) -> None:
        self.local_vars[name] = value

    @staticmethod
    def _is_pathy(elem: Any) -> bool:
        return isinstance(elem, str) or isinstance(elem, Path)

    # Attributes begin here

    # Locations and paths

    @property
    def base_dir(self) -> Path:
        """
        The path that is the base of all other relative paths.

        Default: The directory the config file was loaded from.
        """

        return Path(self._get("base_dir", str, Path)).expanduser()

    @base_dir.setter
    def base_dir(self, path: Path) -> None:
        self._set("base_dir", path)

    def _interpret_path(self, path: Union[str, Path]) -> Path:
        path = Path(path).expanduser()
        if path.is_absolute():
            logger.debug(style_path(path) + " is absolute, no interpreting required")
            return path
        else:
            logger.debug(style_path(path) + " is relative, interpreting as " + style_path(self.base_dir / path))
            return self.base_dir / path

    @property
    def known_files(self) -> Path:
        """
        The path where evering stores which files it is currently
        managing.

        Default: "known_files"
        """

        return self._interpret_path(self._get("known_files", str, Path))

    @property
    def config_dir(self) -> Path:
        """
        The directory containing the config files.

        Default: "config/"
        """

        return self._interpret_path(self._get("config_dir", str, Path))

    # Parsing and compiling behavior

    @property
    def binary(self) -> bool:
        """
        When interpreting a separate header file: Whether the
        corresponding file should not be parsed and compiled, but
        instead just copied to the targets.

        Has no effect if the file has no header files.

        Default: True
        """

        return self._get("binary", bool)

    @property
    def targets(self) -> List[Path]:
        """
        The locations the (compiled) config file should be put
        in. Must be set for all files.

        Default: not set
        """

        name = "targets"
        target = self._get(name)
        is_path = self._is_pathy(target)
        is_list_of_paths = (isinstance(target, list) and
                            all(self._is_pathy(elem) for elem in target))

        if not is_path and not is_list_of_paths:
            raise ConfigurationException(
                style_error("Expected variable ") + style_var(name) +
                style_error(" to be either a path or a list of paths"))

        if is_path:
            return [self._interpret_path(target)]
        else:
            return [self._interpret_path(elem) for elem in target]

    @property
    def statement_prefix(self) -> str:
        """
        This determines the prefix for statements like "# if",
        "# elif", "# else" or "# endif". The prefix always has at
        least length 1.

        Default: "#"
        """

        name = "statement_prefix"
        prefix = self._get(name, str)

        if len(prefix) < 1:
            raise ConfigurationException(
                style_error("Expected variable ") + style_var(name) +
                style_error(" to have at least length 1"))

        return prefix

    @property
    def expression_delimiters(self) -> Tuple[str, str]:
        """
        This determines the delimiters for expressions like
        "{{ 1 + 1 }}".

        It is a tuple of the form: (<prefix>, <suffix>), where both
        the prefix and suffix are strings of at least length 1.

        Default: ("{{", "}}")
        """

        name = "expression_delimiters"
        delimiters = self._get(name, tuple)

        if len(delimiters) != 2:
            raise ConfigurationException(
                style_error("Expected variable ") + style_var(name) +
                style_error(" to be a tuple of length 2"))

        if len(delimiters[0]) < 1 or len(delimiters[1]) < 1:
            raise ConfigurationException(
                style_error("Expected both strings in variable ") +
                style_var(name) + style_error( "to be of length >= 1"))

        return delimiters

    # Environment and file-specific information

    @property
    def filename(self) -> str:
        """
        The name of the file currently being compiled, as a string.

        Only set during compilation.
        """

        return self._get("filename", str)

    @filename.setter
    def filename(self, filename: str) -> None:
        self._set("filename", filename)

    @property
    def target(self) -> Path:
        """
        The location the file is currently being compiled for, as a
        Path.

        Only set during compilation.
        """

        return self._interpret_path(self._get("target", str, Path))

    @target.setter
    def target(self, path: Path) -> None:
        self._set("target", path)

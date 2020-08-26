"""
This module contains helper functions for locating and loading config
files.

The result of loading a config file are the "local" variables,
including the modules loaded via "import".
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .colors import style_error, style_path, style_var
from .util import (ExecuteException, ReadFileException, copy_local_variables,
                   get_host, get_user, read_file, safer_exec)

__all__ = [
    "DEFAULT_LOCATIONS",
    "ConfigurationException",
    "DefaultConfigValue", "DefaultConfig", "DEFAULT_CONFIG",
    "Config",
]
logger = logging.getLogger(__name__)

DEFAULT_LOCATIONS = [
    Path("~/.config/evering/config.py"),
    Path("~/.evering/config.py"),
    Path("~/.evering.py"),
]


class ConfigurationException(Exception):
    pass


@dataclass
class DefaultConfigValue:
    # A short textual description of the value's function
    description: str
    # The actual default value
    value: Any
    # Whether this variable even has a default value or the value is set at
    # runtime
    has_constant_value: bool


class DefaultConfig:
    def __init__(self) -> None:
        self._values: Dict[str, DefaultConfigValue] = {}

    def add(self,
            name: str,
            description: str,
            value: Any = None,
            has_constant_value: bool = True
            ) -> None:
        if name in self._values:
            raise ConfigurationException(f"Value {name!r} already exists")

        self._values[name] = DefaultConfigValue(
            description, value=value, has_constant_value=has_constant_value)

    def get(self, name: str) -> Optional[DefaultConfigValue]:
        return self._values.get(name)

    def to_local_vars(self) -> Dict[str, Any]:
        return {name: d.value
                for name, d in self._values.items()
                if d.has_constant_value}

    def to_config(self) -> "Config":
        config = Config(self.to_local_vars())
        config.user = get_user()
        config.host = get_host()
        return config

    def to_config_file(self) -> str:
        """
        Attempt to convert the DefaultConfig into a format that can be read by
        a python interpreter. This assumes that all names are valid variable
        names and that the repr() representations of each object can be read by
        the interpreter.

        This solution is quite hacky, so use at your own risk :P (At least make
        sure that this works with all your default values before you use it).
        """

        lines = ["from pathlib import *", ""]

        for name in sorted(self._values):
            value = self._values[name]

            line: str
            if value.has_constant_value:
                line = f"{name} = {value.value!r}"
            else:
                line = f"# {name}"

            line = f"{line:<32} # {value.description}"
            lines.append(line)

        return "\n".join(lines) + "\n"


DEFAULT_CONFIG = DefaultConfig()

DEFAULT_CONFIG.add(
    "base_dir",
    "All relative paths are interpreted as relative to this directory."
    " Default: The directory the config file was loaded from",
    has_constant_value=False)

DEFAULT_CONFIG.add(
    "known_files",
    "The file where evering stores which files it is currently managing",
    value="known_files")

DEFAULT_CONFIG.add(
    "config_dir",
    "The directory containing the config files",
    value="config")

DEFAULT_CONFIG.add(
    "action_dir",
    "The directory to copy the action scripts to",
    value="actions")

DEFAULT_CONFIG.add(
    "binary",
    ("When interpreting a header file: When True, the corresponding file is "
     "copied directly to the target instead of compiled. Has no effect if a "
     "file has no header file"),
    value=True)

DEFAULT_CONFIG.add(
    "targets",
    ("The locations a config file should be placed in. Either a path or a "
     "list of paths"),
    value=[])

DEFAULT_CONFIG.add(
    "action",
    ("Whether a file should be treated as an action with a certain name. If "
     "set, must be a string"),
    has_constant_value=False)

DEFAULT_CONFIG.add(
    "statement_prefix",
    "Determines the prefix for statements like \"if\"",
    value="#")

DEFAULT_CONFIG.add(
    "expression_delimiters",
    "Determines the delimiters for in-line expressions",
    value=("{{", "}}"))

# Compile-time info

DEFAULT_CONFIG.add(
    "filename",
    ("Name of the file currently being compiled, as a string. Set during "
     "compilation"),
    has_constant_value=False)

DEFAULT_CONFIG.add(
    "target",
    ("Location the file is currently being compiled for, as a Path. Set "
     "during compilation"),
    has_constant_value=False)

DEFAULT_CONFIG.add(
    "user",
    "Current username. Set during compilation",
    has_constant_value=False)

DEFAULT_CONFIG.add(
    "host",
    "Name of the current computer. Set during compilation",
    has_constant_value=False)


class Config:
    @staticmethod
    def load_config_file(path: Optional[Path]) -> "Config":
        """
        May raise: ConfigurationException
        """

        conf = DEFAULT_CONFIG.to_config()

        if path is None:
            # Try out all default config file locations
            for path in DEFAULT_LOCATIONS:
                try:
                    copy = conf.copy()
                    copy.apply_config_file(path)
                    conf = copy
                    break
                except ConfigurationException as e:
                    logger.debug("Tried default config file at "
                                 f"{style_path(path)} and it didn't work: {e}")
            else:
                raise ConfigurationException(style_error(
                    "No valid config file found in any of the default "
                    "locations"
                ))
        else:
            # Use the path
            try:
                copy = conf.copy()
                copy.apply_config_file(path)
                conf = copy
            except (ReadFileException, ExecuteException) as e:
                raise ConfigurationException(
                    style_error("Could not load config file from ") +
                    style_path(path) + f": {e}")

        return conf

    def __init__(self, local_vars: Dict[str, Any]) -> None:
        self.local_vars = local_vars

    def apply_config_file(self, path: Path) -> None:
        """
        May raise: ConfigurationException
        """

        if "base_dir" not in self.local_vars:
            self.local_vars["base_dir"] = path.parent

        try:
            safer_exec(read_file(path), self.local_vars)
        except (ReadFileException, ExecuteException) as e:
            error_msg = f"Could not load config from {style_path(path)}: {e}"
            logger.debug(error_msg)
            raise ConfigurationException(error_msg)
        else:
            logger.info(f"Loaded config from {style_path(path)}")

    def copy(self) -> "Config":
        return Config(copy_local_variables(self.local_vars))

    def _get(self, name: str, *types: type) -> Any:
        """
        May raise: ConfigurationException
        """

        if name not in self.local_vars:
            raise ConfigurationException(
                style_error("Expected a variable named ") +
                style_var(name)
            )

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
        if name not in self.local_vars:
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
        return Path(self._get("base_dir", str, Path)).expanduser()

    @base_dir.setter
    def base_dir(self, path: Path) -> None:
        self._set("base_dir", path)

    def _interpret_path(self, path: Union[str, Path]) -> Path:
        path = Path(path).expanduser()
        if path.is_absolute():
            logger.debug(f"{style_path(path)} is absolute, no interpreting "
                         "required")
            return path
        else:
            logger.debug(f"{style_path(path)} is relative, interpreting as "
                         f"{style_path(self.base_dir / path)}")
            return self.base_dir / path

    @property
    def known_files(self) -> Path:
        return self._interpret_path(self._get("known_files", str, Path))

    @property
    def config_dir(self) -> Path:
        return self._interpret_path(self._get("config_dir", str, Path))

    @property
    def action_dir(self) -> Path:
        return self._interpret_path(self._get("action_dir", str, Path))

    # Parsing and compiling behavior

    @property
    def binary(self) -> bool:
        return self._get("binary", bool)

    @property
    def targets(self) -> List[Path]:
        name = "targets"
        targets = self._get(name)

        # Check whether targets argument has the correct format
        is_path = self._is_pathy(targets)
        is_list_of_paths = (isinstance(targets, list) and
                            all(self._is_pathy(elem) for elem in targets))
        if not is_path and not is_list_of_paths:
            raise ConfigurationException(
                style_error("Expected variable ") + style_var(name) +
                style_error(" to be either a path or a list of paths"))

        paths: List[Path]
        if is_path:
            paths = [self._interpret_path(targets)]
        else:
            paths = [self._interpret_path(elem) for elem in targets]

        # If this is an action, just treat it like yet another target in a very
        # specific location
        if self.action is not None:
            paths.append(self.action_dir / self.action)

        return paths

    @property
    def action(self) -> Optional[str]:
        return self._get_optional("action", str)

    @property
    def statement_prefix(self) -> str:
        name = "statement_prefix"
        prefix = self._get(name, str)

        if len(prefix) < 1:
            raise ConfigurationException(
                style_error("Expected variable ") + style_var(name) +
                style_error(" to have at least length 1"))

        return prefix

    @property
    def expression_delimiters(self) -> Tuple[str, str]:
        name = "expression_delimiters"
        delimiters = self._get(name, tuple)

        if len(delimiters) != 2:
            raise ConfigurationException(
                style_error("Expected variable ") + style_var(name) +
                style_error(" to be a tuple of length 2"))

        if len(delimiters[0]) < 1 or len(delimiters[1]) < 1:
            raise ConfigurationException(
                style_error("Expected both strings in variable ") +
                style_var(name) + style_error("to be of length >= 1"))

        return delimiters

    # Environment and file-specific information

    @property
    def filename(self) -> str:
        return self._get("filename", str)

    @filename.setter
    def filename(self, filename: str) -> None:
        self._set("filename", filename)

    @property
    def target(self) -> Path:
        return self._interpret_path(self._get("target", str, Path))

    @target.setter
    def target(self, path: Path) -> None:
        self._set("target", path)

    @property
    def user(self) -> str:
        return self._get("user", str)

    @target.setter
    def user(self, user: str) -> None:
        self._set("user", user)

    @property
    def host(self) -> str:
        return self._get("host", str)

    @target.setter
    def host(self, host: str) -> None:
        self._set("host", host)

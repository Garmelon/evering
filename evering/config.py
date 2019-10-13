"""
This module contains helper functions for locating and loading config
files.

The result of loading a config file are the "local" variables,
including the modules loaded via "import".
"""

from pathlib import Path

__all__ = []

DEFAULT_LOCATIONS = [
    Path("~/.config/evering/config"),
    Path("~/.evering/config"),
    Path("~/.evering.conf"),
]

class LoadConfigException(Exception):
    pass

def load_config(path: Path = None) -> Dict[str, Any]:
    if path is not None:
        return load_config_file(path)
    else:
        for path in DEFAULT_LOCATIONS:
            try:
                return load_config_file(path)
            except LoadConfigException:
                # Try the next default location
                # TODO print a log message
                pass
        else:
            raise LoadConfigException("no config file found in any of the default locations")

def load_config_file(path: Path) -> Dict[str, Any]:
    try:
        with open(path) as f:
            l = {}
            exec(f.read(), locals=l, globals={})
            return l
    except IOException as e:
        raise LoadConfigException(str(e))

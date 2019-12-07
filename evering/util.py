import copy
import getpass
import socket
import types
from pathlib import Path
from typing import Any, Dict

__all__ = [
    "copy_local_variables",
    "get_user", "get_host",
    "ExecuteException", "safer_exec", "safer_eval",
    "ReadFileException", "read_file",
    "WriteFileException", "write_file",
    "CatastrophicError", "LessCatastrophicError",
]

def copy_local_variables(local: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attempts to deep-copy a set of local variables, but keeping
    modules at the top level alone, since they don't tend to deepcopy
    well.

    May raise: Not sure at the moment
    """

    local_copy = {}

    for key, value in local.items():
        if isinstance(value, types.ModuleType):
            local_copy[key] = value
        else:
            local_copy[key] = copy.deepcopy(value)

    return local_copy

def get_user() -> str:
    return getpass.getuser()

def get_host() -> str:
    return socket.gethostname()

class ExecuteException(Exception):
    pass

def safer_exec(code: str, local_vars: Dict[str, Any]) -> None:
    """
    May raise: ExecuteException
    """

    try:
        exec(code, {}, local_vars)
    except Exception as e:
        raise ExecuteException(e)

def safer_eval(code: str, local_vars: Dict[str, Any]) -> Any:
    """
    May raise: ExecuteException
    """

    try:
        return eval(code, {}, local_vars)
    except Exception as e:
        raise ExecuteException(e)

class ReadFileException(Exception):
    pass

def read_file(path: Path) -> str:
    """
    May raise: ReadFileException
    """

    try:
        with open(path.expanduser()) as f:
            return f.read()
    except OSError as e:
        raise ReadFileException(e)

class WriteFileException(Exception):
    pass

def write_file(path: Path, text: str) -> None:
    """
    May raise: WriteFileException
    """

    try:
        with open(path.expanduser(), "w") as f:
            f.write(text)
    except OSError as e:
        raise WriteFileException(e)

class CatastrophicError(Exception):
    pass

class LessCatastrophicError(Exception):
    pass

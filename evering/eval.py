"""
This module contains helper functions for evaluating python code and
managing local variables.
"""

import copy
import types
from typing import Any, Dict

__all__ = ["copy_local_variables"]

def copy_local_variables(local: Dict[str, Any]) -> Dict[str, Any]:
    local_copy = {}

    for key, value in local:
        if isinstance(value, types.ModuleType):
            local_copy[key] = value
        else:
            local_copy[key] = copy.deepcopy(value)

    return local_copy

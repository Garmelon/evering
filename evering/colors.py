"""
This module includes functions to color the console output with ANSI
escape sequences.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union

__all__ = [
    "CSI", "ERASE_LINE",
    "BOLD", "ITALIC", "UNDERLINE",
    "Color",
    "BLACK", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN", "WHITE", "BRIGHT_BLACK", "BRIGHT_RED", "BRIGHT_GREEN", "BRIGHT_YELLOW", "BRIGHT_BLUE", "BRIGHT_MAGENTA", "BRIGHT_CYAN", "BRIGHT_WHITE",
    "style_sequence", "styled",
    "style_path", "style_var", "style_error", "style_warning",
]

# ANSI escape sequences
# See: https://en.wikipedia.org/wiki/ANSI_escape_code#CSI_sequences

CSI = "\u001b["
ERASE_LINE = f"{CSI}2K"

# Styles

BOLD = 1
ITALIC = 3
UNDERLINE = 4

# Colors

@dataclass
class Color:
    fg: int
    bg: int

BLACK = Color(30, 40)
RED = Color(31, 41)
GREEN = Color(32, 42)
YELLOW = Color(33, 43)
BLUE = Color(34, 44)
MAGENTA = Color(35, 45)
CYAN = Color(36, 46)
WHITE = Color(37, 47)
BRIGHT_BLACK = Color(90, 100)
BRIGHT_RED = Color(91, 101)
BRIGHT_GREEN = Color(92, 102)
BRIGHT_YELLOW = Color(93, 103)
BRIGHT_BLUE = Color(94, 104)
BRIGHT_MAGENTA = Color(95, 105)
BRIGHT_CYAN = Color(96, 106)
BRIGHT_WHITE = Color(97, 107)

def style_sequence(*args: int) -> str:
    arglist = ";".join(str(arg) for arg in args)
    return f"{CSI}{arglist}m"

def styled(text: str, *args: int) -> str:
    if args:
        sequence = style_sequence(*args)
        reset = style_sequence()
        return f"{sequence}{text}{reset}"
    else:
        return text # No styling necessary

def style_path(path: Union[str, Path]) -> str:
    if isinstance(path, Path):
        path = str(path)
    return styled(path, BRIGHT_BLACK.fg, BOLD)

def style_var(text: str) -> str:
    return styled(repr(text), BLUE.fg)

def style_error(text: str) -> str:
    return styled(text, RED.fg, BOLD)

def style_warning(text: str) -> str:
    return styled(text, YELLOW.fg, BOLD)

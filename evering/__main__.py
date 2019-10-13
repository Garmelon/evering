import argparse
from pathlib import Path
from typing import Union
import logging

from .colors import *

logging.basicConfig(level=logging.DEBUG, style="{", format="{levelname:>7}: {message}")
logger = logging.getLogger(__name__)




def command_test_func(args):
    logger.debug(styled("Debug", BLUE.fg, BOLD))
    logger.info(styled("Info", GREEN.fg, BOLD))
    logger.warning(styled("Warning", YELLOW.fg, BOLD))
    logger.error(styled("Error", RED.fg, BOLD))
    logger.info(styled("Test", BRIGHT_BLACK.fg, BOLD))












def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config-file")
    subparsers = parser.add_subparsers(title="commands")

    command_test = subparsers.add_parser("test")
    command_test.set_defaults(func=command_test_func)
    command_test.add_argument("some_file")

    args = parser.parse_args()
    if "func" in args:
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

import argparse
import logging
from pathlib import Path
from typing import Any

from .colors import style_path, style_warning
from .config import DEFAULT_CONFIG, Config, ConfigurationException
from .explore import find_config_files
from .known_files import KnownFiles
from .process import Processor
from .prompt import prompt_choice
from .util import CatastrophicError, LessCatastrophicError

LOG_STYLE = "{"
LOG_FORMAT = "{levelname:>7}: {message}"
# logging.basicConfig(level=logging.DEBUG, style="{", format="{levelname:>7}: {message}")
# logging.basicConfig(level=logging.INFO, style="{", format="{levelname:>7}: {message}")
logger = logging.getLogger(__name__)

HEADER_FILE_SUFFIX = ".evering-header"

"""
(error) -> CatastrophicError
(warning) -> log message
(skip/abort) -> LessCatastrophicError

- Load config
  - no readable config file found (error)
  - config file can't be found (error)
  - config file can't be opened (error)
  - config file contains invalid syntax (error)

- Load known files
  - known_files can't be read (error)
  - known_files contains invalid syntax (error)
  - known_files contains invalid data (error)


- Locate config files + header files
  - missing permissions to view folders (warning)
  - header file but no corresponding file (warning)

- Process files


Processing files
================

Header problems:
- header file can't be read (skip/abort)
- invalid header syntax (skip/abort)

Config file problems:
- file can't be read (skip/abort)
- file contains no lines (warning)
- invalid config file syntax (skip/abort)
- error while compiling (skip/abort)

Writing problems:
- no targets (skip/abort)
- can't write/copy to target (warning)
- can't write to known files (error)
"""


def run(args: Any) -> None:
    config = Config.load_config_file(args.config_file
                                     and Path(args.config_file) or None)
    known_files = KnownFiles(config.known_files)

    processor = Processor(config, known_files)
    config_files = find_config_files(config.config_dir)

    for file_info in config_files:
        try:
            processor.process_file(file_info.path, file_info.header,
                                   dry_run=args.dry_run)
        except LessCatastrophicError as e:
            logger.error(e)

            if prompt_choice("[C]ontinue to the next file or [A]bort the "
                             "program?", "Ca") == "a":
                raise CatastrophicError("Aborted")

    if args.dry_run:
        return

    for path in known_files.find_forgotten_files():
        logger.info(style_warning("The file ") + style_path(path)
                    + style_warning(" is no longer known"))

    known_files.save_final()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config-file", type=Path)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--dry-run", action="store_true")
    parser.add_argument("--export-default-config", type=Path)
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, style=LOG_STYLE, format=LOG_FORMAT)

    if args.export_default_config is not None:
        logger.info("Exporting default config to "
                    f"{style_path(args.export_default_config)}")
        with open(args.export_default_config, "w") as f:
            f.write(DEFAULT_CONFIG.to_config_file())
        return

    try:
        run(args)
    except CatastrophicError as e:
        logger.error(e)
    except ConfigurationException as e:
        logger.error(e)


if __name__ == "__main__":
    main()

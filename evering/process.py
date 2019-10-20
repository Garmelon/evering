import logging
import shutil
from pathlib import Path
from typing import List, Optional

from .colors import *
from .config import *
from .known_files import *
from .parser import *
from .util import *

__all__ = ["Processor"]
logger = logging.getLogger(__name__)

class Processor:
    def __init__(self, config: Config, known_files: KnownFiles) -> None:
        self.config = config
        self.known_files = known_files

    def process_file(self, path: Path, header_path: Optional[Path] = None) -> None:
        logger.info(f"{style_path(path)}:")

        config = self.config.copy()
        config.filename = path.name

        if header_path is None:
            self._process_file_without_header(path, config)
        else:
            self._process_file_with_header(path, header_path, config)

    def _process_file_without_header(self, path: Path, config: Config) -> None:
        logger.debug(f"Processing file {style_path(path)} with no header")

        try:
            text = read_file(path)
        except ReadFileException as e:
            raise LessCatastrophicError(
                style_error("Could not load file ") +
                style_path(path) + f": {e}")
        
        header, lines = split_header_and_rest(text)

        try:
            safer_exec("\n".join(header), config.local_vars)
        except ExecuteException as e:
            raise LessCatastrophicError(
                style_error("Could not parse header of file ") +
                style_path(path) + f": {e}")
        
        self._process_parseable(lines, config)

    def _process_file_with_header(self, path: Path, header_path: Path, config: Config) -> None:
        logger.debug(f"Processing file {style_path(path)} "
                     f"with header {style_path(header_path)}")

        try:
            header_text = read_file(header_path)
            safer_exec(header_text, config.local_vars)
        except ReadFileException as e:
            raise LessCatastrophicError(
                style_error("Could not load header file ") +
                style_path(header_path) + f": {e}")
        except ExecuteException as e:
            raise LessCatastrophicError(
                style_error("Could not parse header file ") +
                style_path(header_path) + f": {e}")

        if config.binary:
            self._process_binary(path, config)
        else:
            try:
                lines = read_file(path).splitlines()
            except ReadFileException as e:
                raise LessCatastrophicError(
                    style_error("Could not load file ") +
                    style_path(path) + f": {e}")

            self._process_parseable(lines, config)

    def _process_binary(self, path: Path, config: Config) -> None:
        logger.debug(f"Processing as a binary file")

        for target in config.targets:
            logger.info(f"  -> {style_path(str(target))}")

            try:
                shutil.copy(path, target)
            except (IOError, shutil.SameFileError) as e:
                logger.warning(style_warning("Could not copy") + f": {e}")

    def _process_parseable(self, lines: List[str], config: Config) -> None:
        for target in config.targets:
            logger.info(f"  -> {style_path(str(target))}")

            config_copy = config.copy()
            config_copy.target = target

            try:
                parser = Parser(
                    lines,
                    statement_prefix=config.statement_prefix,
                    expression_prefix=config.expression_delimiters[0],
                    expression_suffix=config.expression_delimiters[1],
                )
                text = parser.evaluate(config_copy.local_vars)
            except ParseException as e:
                logger.warning(style_warning("Could not parse ") +
                               style_path(target) + f": {e}")
                continue
            except ExecuteException as e:
                logger.warning(style_warning("Could not compile ") +
                               style_path(target) + f": {e}")
                continue

            try:
                write_file(target, text)
            except WriteFileException as e:
                logger.warning(style_warning("Could not write to ") + style_path(str(target)) +
                            f": {e}")

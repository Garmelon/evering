import hashlib
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from .colors import *
from .config import *
from .known_files import *
from .parser import *
from .prompt import *
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
        logger.debug(f"Processing file {style_path(path)} without header")

        try:
            text = read_file(path)
        except ReadFileException as e:
            raise LessCatastrophicError(
                style_error("Could not read file ") +
                style_path(path) + f": {e}")

        header, lines = split_header_and_rest(text)

        try:
            safer_exec("\n".join(header), config.local_vars)
        except ExecuteException as e:
            raise LessCatastrophicError(
                style_error("Could not parse header of file ") +
                style_path(path) + f": {e}")

        self._process_parseable(lines, config, path)

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

            self._process_parseable(lines, config, path)

    def _process_binary(self, path: Path, config: Config) -> None:
        logger.debug(f"Processing as a binary file")

        if not config.targets:
            logger.info("  (no targets)")
            return

        for target in config.targets:
            logger.info(f"  -> {style_path(target)}")

            if not self._justify_target(target):
                logger.info("Skipping this target")
                continue

            try:
                target.parent.mkdir(parents=True, exist_ok=True)
            except IOError as e:
                logger.warning(style_warning("Could not create target directory") + f": {e}")
                continue

            try:
                shutil.copy(path, target)
            except (IOError, shutil.SameFileError) as e:
                logger.warning(style_warning("Could not copy") + f": {e}")
                continue

            try:
                shutil.copymode(path, target)
            except shutil.Error as e:
                logger.warning(style_warning("Could not copy permissions") + f": {e}")

            self._update_known_hash(target)

    def _process_parseable(self, lines: List[str], config: Config, source: Path) -> None:
        if not config.targets:
            logger.info("  (no targets)")
            return

        for target in config.targets:
            logger.info(f"  -> {style_path(target)}")

            if not self._justify_target(target):
                logger.info("Skipping this target")
                continue

            config_copy = config.copy()
            config_copy.target = target

            try:
                parser = Parser(
                    lines,
                    statement_prefix=config.statement_prefix,
                    expression_prefix=config.expression_delimiters[0],
                    expression_suffix=config.expression_delimiters[1],
                )
            except ParseException as e:
                logger.warning(style_warning("Could not parse ") +
                               style_path(target) + f": {e}")
                continue

            try:
                text = parser.evaluate(config_copy.local_vars)
            except ExecuteException as e:
                logger.warning(style_warning("Could not compile ") +
                               style_path(target) + f": {e}")
                continue

            try:
                target.parent.mkdir(parents=True, exist_ok=True)
            except IOError as e:
                logger.warning(style_warning("Could not create target directory") + f": {e}")
                continue

            try:
                write_file(target, text)
            except WriteFileException as e:
                logger.warning(style_warning("Could not write to target") + f": {e}")
                continue

            try:
                shutil.copymode(source, target)
            except shutil.Error as e:
                logger.warning(style_warning("Could not copy permissions") + f": {e}")

            self._update_known_hash(target)

    def _obtain_hash(self, path: Path) -> Optional[str]:
        BLOCK_SIZE = 2**16

        try:
            h = hashlib.sha256()

            with open(path, "rb") as f:
                while True:
                    block = f.read(BLOCK_SIZE)
                    if not block: break
                    h.update(block)

            return h.hexdigest()

        except IOError:
            return None

    def _justify_target(self, target: Path) -> bool:
        if not target.exists():
            return True

        if not target.is_file():
            logger.warning(style_warning("The target is a directory"))
            return False

        if self.known_files.was_recently_modified(target):
            logger.warning(style_warning("This target was already overwritten earlier"))
            return False

        target_hash = self._obtain_hash(target)
        if target_hash is None:
            return prompt_yes_no("Overwriting a file that could not be hashed, continue?", False)

        known_target_hash = self.known_files.get_hash(target)
        if known_target_hash is None:
            return prompt_yes_no("Overwriting an unknown file, continue?", False)

        # The following condition is phrased awkwardly because I just
        # feel better if the final statement in this function is not a
        # 'return True'. After all, returning True here might cause
        # loss of important configuration data.

        if target_hash == known_target_hash:
            # We're positive that this file hasn't changed since we've
            # last seen it.
            return True

        return prompt_yes_no("Overwriting a file that was modified since it was last overwritten, continue?", False)

    def _update_known_hash(self, target: Path) -> None:
        target_hash = self._obtain_hash(target)
        if target_hash is None:
            raise LessCatastrophicError(
                style_error("Could not obtain hash of target file ") +
                style_path(target))

        self.known_files.update_file(target, target_hash)
        self.known_files.save_incremental()

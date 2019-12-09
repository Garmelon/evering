import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from .colors import *
from .util import *

__all__ = ["KnownFiles"]
logger = logging.getLogger(__name__)

class KnownFiles:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._old_known_files: Dict[Path, str] = {}
        self._new_known_files: Dict[Path, str] = {}

        try:
            with open(self._path) as f:
                self._old_known_files = self._read_known_files(f.read())
        except FileNotFoundError as e:
            logger.debug(f"File {style_path(self._path)} does not exist, "
                         "creating a new file on the first upcoming save")

    def _normalize_path(self, path: Path) -> Path:
        return path.expanduser().resolve()

    def _read_known_files(self, text: str) -> Dict[Path, str]:
        known_files: Dict[Path, str] = {}
        raw_known_files = json.loads(text)

        if not isinstance(raw_known_files, dict):
            raise CatastrophicError(style_error("Root level structure is not a dictionary"))

        for path, file_hash in raw_known_files.items():
            if not isinstance(path, str):
                raise CatastrophicError(style_error(f"Path {path!r} is not a string"))
            if not isinstance(file_hash, str):
                raise CatastrophicError(style_error(f"Hash {hash!r} at path {path!r} is not a string"))

            path = self._normalize_path(Path(path))
            known_files[path] = file_hash

        return known_files

    def was_recently_modified(self, path: Path) -> bool:
        return self._normalize_path(path) in self._new_known_files

    def get_hash(self, path: Path) -> Optional[str]:
        path = self._normalize_path(path)

        h = self._new_known_files.get(path)

        if h is None:
            h = self._old_known_files.get(path)

        return h

    def update_file(self, path: Path, file_hash: str) -> None:
        self._new_known_files[self._normalize_path(path)] = file_hash

    def save_incremental(self) -> None:
        to_save: Dict[str, str] = {}
        for path in self._old_known_files.keys() | self._new_known_files.keys():
            if path in self._new_known_files:
                to_save[str(path)] = self._new_known_files[path]
            else:
                to_save[str(path)] = self._old_known_files[path]

        self._save(json.dumps(to_save, indent=2))
        logger.debug(f"Incremental save to {style_path(self._path)} completed")

    def find_forgotten_files(self) -> Set[Path]:
        """
        Finds all files which were not modified this round and thus
        are no longer known (i. e. have been forgotten).
        """

        return set(self._old_known_files.keys() - self._new_known_files.keys())

    def save_final(self) -> None:
        to_save: Dict[str, str] = {}

        for path, file_hash in self._new_known_files.items():
            to_save[str(path)] = file_hash

        self._save(json.dumps(to_save, indent=2))
        logger.debug(f"Final save to {style_path(self._path)} completed")

    def _save(self, text: str) -> None:
        # Append a .tmp to the file name
        path = Path(*self._path.parts[:-1], self._path.name + ".tmp")

        try:
            write_file(path, text)
            path.replace(self._path) # Assumed to be atomic
        except (WriteFileException, OSError) as e:
            raise CatastrophicError(
                style_error("Error saving known files to ") +
                style_path(path) + f": {e}")

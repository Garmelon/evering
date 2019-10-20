import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .colors import *
from .util import *

__all__ = ["FileInfo", "find_config_files"]
logger = logging.getLogger(__name__)

HEADER_FILE_SUFFIX = ".evering-header"

@dataclass
class FileInfo:
    path: Path
    header: Optional[Path] = None

def find_config_files(config_dir: Path) -> List[FileInfo]:
    try:
        return explore_dir(config_dir)
    except OSError as e:
        raise CatastrophicError(style_error("could not access config dir ") + style_path(config_dir) + f": {e}")

def explore_dir(cur_dir: Path) -> List[FileInfo]:
    if not cur_dir.is_dir():
        raise CatastrophicError(style_path(cur_dir) + style_error(" is not a directory"))

    files: Dict[Path, FileInfo] = {}
    header_files: List[Path] = []
    subdirs: List[Path] = []

    # 1. Sort all the files in this folder into their respective categories
    for element in cur_dir.iterdir():
        if element.is_dir():
            logger.debug(f"Found subdir {style_path(element)}")
            subdirs.append(element)
        elif element.is_file():
            if element.suffix == HEADER_FILE_SUFFIX:
                logger.debug(f"Found header file {style_path(element)}")
                header_files.append(element)
            else:
                logger.debug(f"Found file {style_path(element)}")
                files[element] = FileInfo(element)
        else:
            logger.debug(f"{style_path(element)} is neither a dir nor a file")

    # 2. Assign the header files to their respective files
    for header_file in header_files:
        matching_file = header_file.with_suffix("") # Remove last suffix
        matching_file_info = files.get(matching_file)

        if matching_file_info is None:
            logger.warning(style_warning("No corresponding file for header file ") + style_path(header_file))
        else:
            logger.debug(f"Assigned header file {style_path(header_file)} to file {style_path(matching_file)}")
            matching_file_info.header = header_file

    # 3. Collect the resulting FileInfos
    result = list(files.values())

    # 4. And (try to) recursively descend into all folders
    for subdir in subdirs:
        try:
            result.extend(explore_dir(subdir))
        except OSError as e:
            logger.warning(style_warning("Could not descend into folder ") + style_path(subdir) + f": {e}")

    return result

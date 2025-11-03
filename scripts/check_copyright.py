#!/usr/bin/env python

"""Check copyright"""

# Copyright 2018-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import datetime
import logging
import re
import sys
from pathlib import Path


def collect_files(paths: list[str]) -> list[Path]:
    """Collect all valid files from input paths, excluding .pyc files"""
    collected = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_file() and path.suffix != ".pyc":
            collected.append(path)
        elif path.is_dir():
            collected.extend(file for file in path.rglob("*") if file.is_file() and file.suffix != ".pyc")
    return collected


def has_valid_copyright(file_path: Path) -> bool:
    """Check if a file has a valid copyright notice"""
    re_copyright = re.compile(rf"{datetime.datetime.now().year} Florian Pigorsch")
    re_copyright_bad_year = re.compile(r"\d\d\d\d Florian Pigorsch")

    ok = True
    empty = True
    copyright_found = False
    copyright_bad_year_found = False

    try:
        with file_path.open(encoding="utf8") as f:
            for line in f:
                empty = False
                if re_copyright.search(line):
                    copyright_found = True
                    break
                if re_copyright_bad_year.search(line):
                    copyright_bad_year_found = True
                    break
    except (FileNotFoundError, PermissionError, UnicodeDecodeError, OSError) as e:
        msg = f"Could not read {file_path}: {e}"
        logging.getLogger(__name__).warning(msg)
        return True  # Skip unreadable files

    if not empty:
        log = logging.getLogger(__name__)
        if copyright_bad_year_found:
            msg = f"{file_path}: copyright with bad year"
            log.info(msg)
            ok = False
        elif not copyright_found:
            msg = f"{file_path}: no copyright"
            log.info(msg)
            ok = False

    return ok


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    files_to_check = collect_files(sys.argv[1:])
    if not all(has_valid_copyright(file_path) for file_path in files_to_check):
        sys.exit(1)

    sys.exit(0)

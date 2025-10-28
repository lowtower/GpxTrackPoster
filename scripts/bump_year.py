#!/usr/bin/env python

"""Bump year"""

# Copyright 2018-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import datetime
import re
import sys
from pathlib import Path

THIS_YEAR = str(datetime.datetime.now().year)
re_year = re.compile(r"\s(\d\d\d\d) Florian Pigorsch")
re_year_range = re.compile(r"\s(\d\d\d\d)-(\d\d\d\d) Florian Pigorsch")


def bump_year(path: str) -> None:
    """Bump year in a file or all files in a directory."""
    path_obj = Path(path)

    if path_obj.is_dir():
        for file in path_obj.glob("**/*"):  # You can filter with "*.txt" or similar
            if file.is_file() and file.suffix != ".pyc":
                _bump_year_in_file(file)
    elif path_obj.is_file():
        _bump_year_in_file(path_obj)
    else:
        msg = f"Path '{path}' is neither a file nor a directory."
        raise ValueError(msg)


def _bump_year_in_file(file_path: Path) -> None:
    lines = []
    with file_path.open(encoding="utf8") as f:
        for line in f:
            m = re_year.search(line)
            if m and (m.group(1) != THIS_YEAR):
                start, end = m.span(1)
                lines.append(f"{line[:end]}-{THIS_YEAR}{line[end:]}")
                continue

            m = re_year_range.search(line)
            if m and (m.group(2) != THIS_YEAR):
                start, end = m.span(2)
                lines.append(f"{line[:start]}{THIS_YEAR}{line[end:]}")
                continue

            lines.append(line)

    with file_path.open("w", encoding="utf8") as f:
        f.writelines(lines)


if __name__ == "__main__":
    for arg in sys.argv:
        bump_year(arg)

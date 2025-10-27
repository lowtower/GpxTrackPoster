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


def has_valid_copyright(file_name: str) -> bool:
    """Check if a file has a valid copyright notice"""
    re_copyright = re.compile(rf"{datetime.datetime.now().year} Florian Pigorsch")
    re_copyright_bad_year = re.compile(r"\d\d\d\d Florian Pigorsch")

    ok = True
    empty = True
    copyright_found = False
    copyright_bad_year_found = False

    with open(file_name, encoding="utf8") as f:
        for line in f:
            empty = False
            if re_copyright.search(line):
                copyright_found = True
                break
            if re_copyright_bad_year.search(line):
                copyright_bad_year_found = True
                break

    if not empty:
        log = logging.getLogger(__name__)
        if copyright_bad_year_found:
            msg = f"{file_name}: copyright with bad year"
            log.info(msg)
            ok = False
        elif not copyright_found:
            msg = f"{file_name}: no copyright"
            log.info(msg)
            ok = False

    return ok


if not all(has_valid_copyright(file_name) for file_name in sys.argv):
    sys.exit(1)

sys.exit(0)

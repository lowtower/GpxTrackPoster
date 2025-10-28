#!/usr/bin/env python

"""Update README"""

# Copyright 2018-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import sys


def main() -> None:
    """Update README main function"""
    usage = sys.stdin.read()
    if not usage.startswith("usage: create_poster"):
        msg = "Bad usage info from stdin"
        raise RuntimeError(msg)

    readme_md_file_name = sys.argv[1]
    if not readme_md_file_name.endswith("README.md"):
        msg = f"Bad README.md file: {readme_md_file_name}"
        raise RuntimeError(msg)

    # replace usage in README.md
    with open(readme_md_file_name, encoding="utf8") as f:
        lines = f.readlines()

    with open(readme_md_file_name, "w", encoding="utf8") as f:
        state = 0
        for line in lines:
            if state == 0:
                if line.startswith("usage: create_poster"):
                    f.write(usage)
                    state = 1
                else:
                    f.write(line)
            elif state == 1:
                if line.startswith("```"):
                    f.write(line)
                    state = 2
            else:
                f.write(line)


if __name__ == "__main__":
    main()

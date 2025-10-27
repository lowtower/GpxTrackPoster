"""Units"""

# Copyright 2016-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from __future__ import annotations

import pint


class Units:
    """Unit class."""

    _instance = None

    def __init__(self) -> None:
        """Initialize the Units class."""
        if not Units._instance:
            Units._instance = pint.UnitRegistry()

    def __getattr__(self, name: str) -> pint.Unit:
        """Get a unit."""
        return getattr(Units._instance, name)

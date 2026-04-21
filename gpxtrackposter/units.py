# Copyright 2016-2023 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from typing import Any, Optional

import pint  # type: ignore


class Units:
    _instance: Optional[pint.registry.UnitRegistry] = None

    def __init__(self) -> None:
        if not Units._instance:
            Units._instance = pint.UnitRegistry()

    def __getattr__(self, name: str) -> Any:
        return getattr(Units._instance, name)

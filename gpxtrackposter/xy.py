"""Represent x,y values with properly overloaded operations."""

# Copyright 2016-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from __future__ import annotations

from math import isclose


class XY:
    """Represent x,y values with properly overloaded operations."""

    def __init__(self, x: float = 0, y: float = 0) -> None:
        """Initialize a XY."""
        self.x: int | float = x
        self.y: int | float = y

    def __mul__(self, factor: float | XY) -> XY:
        """Multiply this XY by a factor."""
        if isinstance(factor, XY):
            return XY(self.x * factor.x, self.y * factor.y)
        return XY(self.x * factor, self.y * factor)

    def __rmul__(self, factor: float | XY) -> XY:
        """Right multiply this XY by a factor."""
        if isinstance(factor, XY):
            return XY(self.x * factor.x, self.y * factor.y)
        return XY(self.x * factor, self.y * factor)

    def __truediv__(self, divisor: float | XY) -> XY:
        """Divide this XY by a factor."""
        if isinstance(divisor, XY):
            return XY(self.x / divisor.x, self.y / divisor.y)
        return XY(self.x / divisor, self.y / divisor)

    def __add__(self, other: float | XY) -> XY:
        """Add this XY by another XY value."""
        if isinstance(other, XY):
            return XY(self.x + other.x, self.y + other.y)
        return XY(self.x + other, self.y + other)

    def __radd__(self, other: float | XY) -> XY:
        """Right add this XY by another XY value."""
        return self.__add__(other)

    def __sub__(self, other: float | XY) -> XY:
        """Subtract this XY by another XY value."""
        if isinstance(other, XY):
            return XY(self.x - other.x, self.y - other.y)
        return XY(self.x - other, self.y - other)

    def __repr__(self) -> str:
        """Return string representation of this XY value."""
        return f"XY: {self.x}/{self.y}"

    def __eq__(self, other: object) -> bool:
        """Return True if this XY value is equal to another XY value."""
        return isinstance(other, XY) and isclose(self.x, other.x) and isclose(self.y, other.y)

    def __hash__(self) -> int:
        """Return hash value of this XY value."""
        return hash((self.x, self.y))

    def tuple(self) -> tuple[float, float]:
        """Return a tuple with the x and y values.

        Returns:
             Tuple[float, float]: tuple with x and y values.

        """
        return self.x, self.y

    def to_int(self) -> XY:
        """Return an XY object with integer values.

        Returns:
            XY: XY object with integer x and y values.

        """
        return XY(int(self.x), int(self.y))

    def round(self, n: int | None = None) -> XY:
        """Return an XY object with rounded values.

        Returns:
            XY: XY object with rounded x and y values.

        """
        return XY(round(self.x, n), round(self.y, n))

    def get_max(self) -> int | float:
        """Return the maximum of the x and y value.

        Returns:
            int | float: Maximum value.

        """
        return max([self.x, self.y])

    def get_min(self) -> int | float:
        """Return the minimum of the x and y value.

        Returns:
            int | float: minimum value.

        """
        return min([self.x, self.y])

    def scale_to_max_value(self, max_value: float) -> XY:
        """Scale the x and y values to given maximum value.

        Args:
            max_value: Maximum value to scale x and y values to.

        Returns:
            XY: XY object with scaled y and y values.

        """
        if self.x > self.y:
            x = max_value
            y = x / self.x * self.y
        else:
            y = max_value
            x = y / self.y * self.x
        return XY(x, y)

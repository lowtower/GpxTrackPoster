"""Represent a range of numerical values"""

# Copyright 2016-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from typing import Optional


class ValueRange:
    """Represent a range of numerical values.

    Attributes:
        _lower: Lower bound of range.
        _upper: Upper bound of range.

    Methods:
        from_pair: Return a new ValueRange object from a pair of floats.
        is_valid: Return True if lower bound is set, else False.
        lower: Return lower bound.
        upper: Return upper bound.
        diameter: Return difference between upper and lower bounds if valid, else 0.
        contains: Returns True if the range contains value.
        extend: Adjust the range to include value.
        interpolate: Return interpolated value.
        relative_position: Return relative position of value with respect to lower and upper of ValueRange
    """

    def __init__(self) -> None:
        self._lower: Optional[float] = None
        self._upper: Optional[float] = None

    @classmethod
    def from_pair(cls, value1: float, value2: float) -> "ValueRange":
        """Create a value range from a pair of values.

        Args:
            value1: First value.
            value2: Second value.

        Returns:
            ValueRange: Created value range
        """
        r = cls()
        r.extend(value1)
        r.extend(value2)
        return r

    def clear(self) -> None:
        """Clear values of value range"""
        self._lower = None
        self._upper = None

    def is_valid(self) -> bool:
        """Checks whether the value range is valid or not.

        Returns:
            bool: Is the value range valid or not.
        """
        return self._lower is not None

    def lower(self) -> Optional[float]:
        """Returns the lower value of the value range.

        Returns:
            Optional[float]: The lower value of the value range.
        """
        return self._lower

    def upper(self) -> Optional[float]:
        """Returns the upper value of the value range.

        Returns:
            Optional[float]: The upper value of the value range.
        """
        return self._upper

    def diameter(self) -> float:
        """Returns the diameter value of the value range.

        Returns:
            Optional[float]: The diameter value of the value range.
        """
        if self.is_valid():
            assert self._upper is not None
            assert self._lower is not None
            return self._upper - self._lower
        return 0

    def contains(self, value: float) -> bool:
        """Checks whether the value range contains the given value.

        Args:
            value: Value to be checked against containment of value range.

        Returns:
            bool: Value range contains the value or not.
        """
        if not self.is_valid():
            return False

        assert self._upper is not None
        assert self._lower is not None
        return self._lower <= value <= self._upper

    def extend(self, value: float) -> None:
        """Extend the value range contains with the given value.

        Args:
            value: Value to extend the value range with.
        """
        if not self.is_valid():
            self._lower = value
            self._upper = value
        else:
            assert self._upper is not None
            assert self._lower is not None
            self._lower = min(self._lower, value)
            self._upper = max(self._upper, value)

    def interpolate(self, relative: float) -> float:
        """Interpolate the value range with the given relative value.

        Args:
            relative: Value to interpolate the quantity range with.

        Returns:
            float: The interpolated value of the value range.

        Raises:
            ValueError: Value range cannot be interpolated.
        """
        if not self.is_valid():
            raise ValueError("Cannot interpolate invalid ValueRange")
        assert self._lower is not None
        assert self._upper is not None
        return self._lower + relative * (self._upper - self._lower)

    def relative_position(self, value: float) -> float:
        """Get the relative position of the given value within the value range.

        Args:
            value: Value to get the relative position for.

        Returns:
            float: The relative position within the value range.

        Raises:
            ValueError: Relative position cannot be evaluated from the value range.
        """
        if not self.is_valid():
            raise ValueError("Cannot get relative_position for invalid ValueRange")
        assert self._lower is not None
        assert self._upper is not None
        if value <= self._lower:
            return 0.0
        if value >= self._upper:
            return 1.0
        diff = self._upper - self._lower
        if diff == 0:
            return 0.0
        return (value - self._lower) / diff

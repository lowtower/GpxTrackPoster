"""Represent a range of pint quantities"""

# Copyright 2016-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from typing import Optional

import pint  # type: ignore


class QuantityRange:
    """Represent a range of numerical values.

    Attributes:
        _lower: Lower bound of range.
        _upper: Upper bound of range.

    Methods:
        from_pair: Return a new QuantityRange object from a pair of Quantity objects.
        is_valid: Return True if lower bound is set, else False.
        lower: Return lower bound.
        upper: Return upper bound.
        diameter: Return difference between upper and lower bounds if valid, else Quantity(0).
        contains: Returns True if the range contains Quantity value.
        extend: Adjust the range to include Quantity value.
        interpolate: Return interpolated Quantity value
        relative_position: Return relative position of value with respect to lower and upper of QuantityRange
    """

    def __init__(self) -> None:
        self._lower: Optional[pint.Quantity] = None
        self._upper: Optional[pint.Quantity] = None

    @classmethod
    def from_pair(cls, value1: pint.Quantity, value2: pint.Quantity) -> "QuantityRange":
        """Create a quantity range from a pair of values.

        Args:
            value1: First value.
            value2: Second value.

        Returns:
            QuantityRange: Created quantity range
        """
        r = cls()
        r.extend(value1)
        r.extend(value2)
        return r

    def clear(self) -> None:
        """Clear values of quantity range"""
        self._lower = None
        self._upper = None

    def is_valid(self) -> bool:
        """Checks whether the quantity range is valid or not.

        Returns:
            bool: Is the quantity range valid or not.
        """
        return self._lower is not None

    def lower(self) -> Optional[pint.Quantity]:
        """Returns the lower value of the quantity range.

        Returns:
            Optional[pint.Quantity]: The lower value of the quantity range.
        """
        return self._lower

    def upper(self) -> Optional[pint.Quantity]:
        """Returns the upper value of the quantity range.

        Returns:
            Optional[pint.Quantity]: The upper value of the quantity range.
        """
        return self._upper

    def diameter(self) -> pint.Quantity:
        """Returns the diameter value of the quantity range.

        Returns:
            Optional[pint.Quantity]: The diameter value of the quantity range.
        """
        if self.is_valid():
            assert self._upper is not None
            assert self._lower is not None
            return self._upper - self._lower
        return pint.Quantity(0)

    def contains(self, value: pint.Quantity) -> bool:
        """Checks whether the quantity range contains the given value.

        Args:
            value: Value to be checked against containment of quantity range.

        Returns:
            bool: Quantity range contains the value or not.
        """
        if not self.is_valid():
            return False

        assert self._upper is not None
        assert self._lower is not None
        return self._lower <= value <= self._upper

    def extend(self, value: pint.Quantity) -> None:
        """Extend the quantity range contains with the given value.

        Args:
            value: Value to extend the quantity range with.
        """
        if not self.is_valid():
            self._lower = value
            self._upper = value
        else:
            assert self._upper is not None
            assert self._lower is not None
            self._lower = min(self._lower, value)
            self._upper = max(self._upper, value)

    def interpolate(self, relative: float) -> pint.Quantity:
        """Interpolate the quantity range with the given relative value.

        Args:
            relative: Value to interpolate the quantity range with.

        Returns:
            pint.Quantity: The interpolated value of the quantity range.

        Raises:
            ValueError: Quantity range cannot be interpolated.
        """
        if not self.is_valid():
            raise ValueError("Cannot interpolate invalid QuantityRange")
        assert self._lower is not None
        assert self._upper is not None
        return self._lower + relative * (self._upper - self._lower)

    def relative_position(self, value: pint.Quantity) -> float:
        """Get the relative position of the given value within the quantity range.

        Args:
            value: Value to get the relative position for.

        Returns:
            float: The relative position within the quantity range.

        Raises:
            ValueError: Relative position cannot be evaluated from the quantity range.
        """
        if not self.is_valid():
            raise ValueError("Cannot get relative_position for invalid QuantityRange")
        assert self._lower is not None
        assert self._upper is not None
        if value <= self._lower:
            return 0.0
        if value >= self._upper:
            return 1.0
        diff = self._upper - self._lower
        if diff == 0:
            return 0.0
        return ((value - self._lower) / diff).magnitude

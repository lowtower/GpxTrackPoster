"""Contains the base class TracksDrawer, which other Drawers inherit from."""
# Copyright 2016-2023 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import argparse

import pint  # type: ignore
import svgwrite  # type: ignore

from gpxtrackposter import utils
from gpxtrackposter.poster import Poster
from gpxtrackposter.quantity_range import QuantityRange
from gpxtrackposter.xy import XY


class TracksDrawer:
    """Base class that other drawer classes inherit from."""

    def __init__(self, the_poster: Poster):
        self.poster = the_poster

    def create_args(self, args_parser: argparse.ArgumentParser) -> None:
        """Add arguments to the parser.

        Args:
            args_parser: ArgumentParser
        """

    def fetch_args(self, args: argparse.Namespace) -> None:
        """Get arguments from the parser.

        Args:
            args: Namespace

        """

    def draw(self, dr: svgwrite.Drawing, g: svgwrite.container.Group, size: XY, offset: XY) -> None:
        """Draw the circular Poster using distances broken down by time.

        Args:
            dr: svg drawing
            g: svg group
            size: Size
            offset: Offset
        """

    def color(self, length_range: QuantityRange, length: pint.Quantity, is_special: bool = False) -> str:
        """Define special color.

        Args:
            length_range: length range for special color.
            length: length for special color.
            is_special: special track for special color.

        Returns:
            str: Track color.
        """
        color1 = self.poster.colors["special"] if is_special else self.poster.colors["track"]
        color2 = self.poster.colors["special2"] if is_special else self.poster.colors["track2"]
        return utils.interpolate_color(color1, color2, length_range.relative_position(length))

"""Assorted utility methods for use in creating posters."""

# Copyright 2016-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from __future__ import annotations

import locale
import math
from itertools import count as itercount
from itertools import takewhile
from typing import TYPE_CHECKING

import colour  # type: ignore[import-untyped]

if TYPE_CHECKING:
    import s2sphere  # type: ignore[import-untyped]

from gpxtrackposter.value_range import ValueRange
from gpxtrackposter.xy import XY


# mercator projection
def latlng2xy(latlng: s2sphere.LatLng) -> XY:
    """Return an XY object from Latitude and Longitude.

    Args:
        latlng: Latitude and Longitude.

    Returns:
        XY: XY object from Latitude and Longitude.

    """
    return XY(lng2x(latlng.lng().degrees), lat2y(latlng.lat().degrees))


def lng2x(lng_deg: float) -> float:
    """Return an X value from a Longitude.

    Args:
        lng_deg: Longitude in degrees.

    Returns:
        float: X value from Longitude.

    """
    return lng_deg / 180 + 1


def lat2y(lat_deg: float) -> float:
    """Return a Y value from a Latitude.

    Args:
        lat_deg: Latitude in degrees.

    Returns:
        float: Y value from Latitude.

    """
    return 0.5 - math.log(math.tan(math.pi / 4 * (1 + lat_deg / 90))) / math.pi


def project(
    bbox: s2sphere.LatLngRect, size: XY, offset: XY, latlnglines: list[list[s2sphere.LatLng]]
) -> list[list[tuple[float, float]]]:
    """Project latitude, longitude lines to a boundary box with size and offset.

    Args:
        bbox: boundary box
        size: size
        offset: offset
        latlnglines: Latitude, longitude lines

    Returns:
        list[list[tuple[float, float]]]: List of tuples of x and y float values.

    """
    min_x = lng2x(bbox.lng_lo().degrees)
    d_x = lng2x(bbox.lng_hi().degrees) - min_x
    while d_x >= 2:
        d_x -= 2
    while d_x < 0:
        d_x += 2
    min_y = lat2y(bbox.lat_lo().degrees)
    max_y = lat2y(bbox.lat_hi().degrees)
    d_y = abs(max_y - min_y)

    scale = size.x / d_x if size.x / size.y <= d_x / d_y else size.y / d_y
    offset = offset + 0.5 * (size - scale * XY(d_x, -d_y)) - scale * XY(min_x, min_y)
    lines = []
    for latlngline in latlnglines:
        line = []
        for latlng in latlngline:
            if bbox.contains(latlng):
                line.append((offset + scale * latlng2xy(latlng)).tuple())
            elif len(line) > 0:
                lines.append(line)
                line = []
        if len(line) > 0:
            lines.append(line)
    return lines


def compute_bounds_xy(lines: list[list[XY]]) -> tuple[ValueRange, ValueRange]:
    """Compute boundaries of a list of XY objects.

    Args:
        lines: list of XY objects.

    Returns:
        tuple[ValueRange, ValueRange]: Tuple of boundary value ranges for x and y.

    """
    range_x = ValueRange()
    range_y = ValueRange()
    for line in lines:
        for xy in line:
            range_x.extend(xy.x)
            range_y.extend(xy.y)
    return range_x, range_y


def compute_grid(count: int, dimensions: XY) -> tuple[float | None, tuple[int, int] | None]:
    """Compute a grid with a given number of fields and dimensions.

    Args:
        count: Number of fields to generate grid for.
        dimensions: Dimensions of grid.

    Returns:
        tuple[Optional[float], Optional[tuple[int, int]]]: Tuple of best size and best counts for y and y.

    """
    # this is somehow suboptimal O(count^2). I guess it's possible in O(count)
    min_waste = -1.0
    best_size = None
    best_counts = None
    for count_x in range(1, count + 1):
        size_x = dimensions.x / count_x
        for count_y in range(1, count + 1):
            if count_x * count_y >= count:
                size_y = dimensions.y / count_y
                size = min(size_x, size_y)
                waste = dimensions.x * dimensions.y - count * size * size
                if waste < 0:
                    continue
                if best_size is None or waste < min_waste:
                    best_size = size
                    best_counts = count_x, count_y
                    min_waste = waste
    return best_size, best_counts


def interpolate_color(color1: str, color2: str, ratio: float) -> str:
    """Interpolates a color with a ratio between two colors.

    Args:
        color1: First color.
        color2: Second color.
        ratio: Ratio between first and second color.

    Returns:
        str: Interpolated color.

    """
    if ratio < 0:
        ratio = 0
    elif ratio > 1:
        ratio = 1
    c1 = colour.Color(color1)
    c2 = colour.Color(color2)
    c3 = colour.Color(
        hue=((1 - ratio) * c1.hue + ratio * c2.hue),
        saturation=((1 - ratio) * c1.saturation + ratio * c2.saturation),
        luminance=((1 - ratio) * c1.luminance + ratio * c2.luminance),
    )
    return c3.hex_l


def format_float(f: float) -> str:
    """Format a float value to a one digit str.

    Args:
        f: float value.

    Returns:
        str: Formatted value.

    """
    return locale.format_string("%.1f", f)


def make_key_times(year_count: int) -> list[str]:
    """Should append `1` because the svg keyTimes rule

    Args:
        year_count: year run date count

    Returns:
        typing.list[str]: list of key times points

    """
    s = list(takewhile(lambda n: n < 1, itercount(0, 1 / year_count)))
    s.append(1)
    return [str(round(i, 2)) for i in s]

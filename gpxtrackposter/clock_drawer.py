"""Draw a clock Poster."""
# Copyright 2016-2021 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import argparse
import calendar
import datetime
import math
import typing

import svgwrite  # type: ignore

from gpxtrackposter import utils
from gpxtrackposter.exceptions import PosterError
from gpxtrackposter.poster import Poster
from gpxtrackposter.track import Track
from gpxtrackposter.tracks_drawer import TracksDrawer
from gpxtrackposter.value_range import ValueRange
from gpxtrackposter.xy import XY


class ClockDrawer(TracksDrawer):
    """Draw a clock Poster for each of the Poster's tracks.

    Attributes:
        _hours: True if hours lines  should be drawn, else False.
        _hour_color: Color of hour lines.

    Methods:
        create_args: Set up an argparser for clock poster options.
        fetch_args: Get args from argparser.
        draw: Draw each year on the Poster.
    """

    def __init__(self, the_poster: Poster) -> None:
        """Init the ClockDrawer with default values for _hours and _hour_color

        Note that these can be overridden via arguments when calling."""
        super().__init__(the_poster)
        self._hours = False
        self._hour_color = "darkgrey"

    def create_args(self, args_parser: argparse.ArgumentParser) -> None:
        """Add arguments to the parser"""
        group = args_parser.add_argument_group("Clock Type Options")
        group.add_argument(
            "--clock-hours",
            dest="clock_hours",
            action="store_true",
            help="Draw hour lines.",
        )
        group.add_argument(
            "--clock-hour-color",
            dest="clock_hour_color",
            metavar="COLOR",
            type=str,
            default="darkgrey",
            help="Color of hour lines.",
        )

    def fetch_args(self, args: argparse.Namespace) -> None:
        """Get arguments from the parser"""
        self._hours = args.clock_hours
        self._hour_color = args.clock_hour_color

    def draw(self, dr: svgwrite.Drawing, g: svgwrite.container.Group, size: XY, offset: XY) -> None:
        """Draw the clock Poster using distances broken down by time"""
        if self.poster.tracks is None:
            raise PosterError("No tracks to draw.")
        if self.poster.length_range_by_date is None:
            return

        years = self.poster.years.count()
        _, counts = utils.compute_grid(years, size)
        if counts is None:
            raise PosterError("Unable to compute grid.")
        count_x, count_y = counts[0], counts[1]
        x, y = 0, 0
        cell_size = size * XY(1 / count_x, 1 / count_y)
        margin = XY(4, 4)
        if count_x <= 1:
            margin.x = 0
        if count_y <= 1:
            margin.y = 0
        sub_size = cell_size - 2 * margin
        for year in self.poster.years.iter():
            g_year = dr.g(id=f"year{year}")
            g.add(g_year)
            self._draw_year(dr, g_year, sub_size, offset + margin + cell_size * XY(x, y), year)
            x += 1
            if x >= count_x:
                x = 0
                y += 1

    def _draw_year(self, dr: svgwrite.Drawing, g: svgwrite.container.Group, size: XY, offset: XY, year: int) -> None:
        min_size = min(size.x, size.y)
        outer_radius = 0.5 * min_size - 6
        radius_range = ValueRange.from_pair(outer_radius / 6, outer_radius)
        center = offset + 0.5 * size

        if self._hours:
            self._draw_hours(dr, g, center, radius_range)

        year_style = f"dominant-baseline: central; font-size:{min_size * 4.0 / 80.0}px; font-family:Arial;"

        g.add(
            dr.text(
                f"{year}",
                insert=center.tuple(),
                fill=self.poster.colors["text"],
                text_anchor="middle",
                alignment_baseline="middle",
                style=year_style,
            )
        )
        g.add(
            dr.circle(
                center=center.tuple(),
                r=radius_range.lower(),
                stroke=self._hour_color,
                stroke_opacity="0.2",
                fill="none",
                stroke_width=0.3,
            )
        )
        g.add(
            dr.circle(
                center=center.tuple(),
                r=radius_range.upper(),
                stroke=self._hour_color,
                stroke_opacity="0.2",
                fill="none",
                stroke_width=0.3,
            )
        )
        d_rad = (radius_range.upper() - radius_range.lower()) / (366 if calendar.isleap(year) else 365)
        day = 0
        date = datetime.date(year, 1, 1)
        animate_index = 1
        radius = radius_range.lower()
        while date.year == year:
            text_date = date.strftime("%Y-%m-%d")
            year_count = self.poster.year_tracks_date_count_dict[year]
            key_times_list = utils.make_key_times(year_count)
            key_times_len = len(key_times_list)
            if text_date in self.poster.tracks_by_date:
                values = ""
                if self.poster.with_animation:
                    values = ";".join(["0"] * animate_index) + ";" + ";".join(["1"] * (key_times_len - animate_index))
                self._draw_circle_segment(
                    dr,
                    g,
                    self.poster.tracks_by_date[text_date],
                    radius,
                    center,
                    values=values,
                    key_times=";".join(key_times_list),
                )
                animate_index += 1
            day += 1
            date += datetime.timedelta(1)
            radius += d_rad

    def _draw_hours(
        self, dr: svgwrite.Drawing, g: svgwrite.container.Group, center: XY, radius_range: ValueRange
    ) -> None:
        line_length = min([radius_range.upper() / 30, 10.0])
        for angle in range(0, 360, 30):
            start_pos = center + XY(
                math.cos(math.radians(angle)) * radius_range.upper(),
                math.sin(math.radians(angle)) * radius_range.upper(),
            )
            end_pos = center + XY(
                math.cos(math.radians(angle)) * (radius_range.upper() + line_length),
                math.sin(math.radians(angle)) * (radius_range.upper() + line_length),
            )
            g.add(
                dr.line(
                    start=start_pos.tuple(),
                    end=end_pos.tuple(),
                    stroke=self._hour_color,
                    stroke_opacity="0.2",
                    fill="none",
                    stroke_width=0.3,
                )
            )

    def _draw_circle_segment(
        self,
        dr: svgwrite.Drawing,
        g: svgwrite.container.Group,
        tracks: typing.List[Track],
        radius: float,
        center: XY,
        values: str = "",
        key_times: str = "",
    ) -> None:
        length = sum([t.length() for t in tracks])
        has_special = len([t for t in tracks if t.special]) > 0
        color = self.color(self.poster.length_range_by_date, length, has_special)

        a1 = math.radians(utils.get_clock_angle_from_time(tracks[0].start_time().time()))
        a2 = math.radians(utils.get_clock_angle_from_time(tracks[-1].end_time().time()))
        sin_a1, cos_a1 = math.sin(a1), math.cos(a1)
        sin_a2, cos_a2 = math.sin(a2), math.cos(a2)
        path = dr.path(
            d=f"M {center.x + radius * sin_a1} {center.y - radius * cos_a1} ",
            fill="none",
            stroke=color,
            stroke_width=0.2,
        )
        path.push(f"a{radius},{radius} 0 0,1 {radius * (sin_a2 - sin_a1)},{radius * (cos_a1 - cos_a2)}")
        date_title = str(tracks[0].start_time().date())
        str_length = utils.format_float(self.poster.m2u(length))
        path.set_desc(title=f"{date_title} {str_length} {self.poster.u()}")
        if self.poster.with_animation:
            path.add(
                svgwrite.animate.Animate(
                    "opacity",
                    dur=f"{self.poster.animation_time}s",
                    values=values,
                    keyTimes=key_times,
                    repeatCount="indefinite",
                )
            )
        g.add(path)

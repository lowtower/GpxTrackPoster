"""Draw a heatmap poster."""
# Copyright 2016-2021 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import argparse
import logging
import math
import os
import typing
import uuid

import s2sphere  # type: ignore
import staticmaps  # type: ignore
import svgwrite  # type: ignore
from PIL import Image  # type: ignore

from gpxtrackposter import utils
from gpxtrackposter.exceptions import ParameterError
from gpxtrackposter.poster import Poster
from gpxtrackposter.tracks_drawer import TracksDrawer
from gpxtrackposter.xy import XY

log = logging.getLogger(__name__)


class HeatmapDrawer(TracksDrawer):
    """Draw a heatmap Poster based on the tracks.

    Attributes:
        center: Center of the heatmap.
        radius: Scale the heatmap so that a circle with radius (in KM) is visible.

    Methods:
        Create_args: Create arguments for heatmap.
        fetch_args: Get arguments passed.
        draw: Draw the heatmap based on the Poster's tracks.

    """

    def __init__(self, the_poster: Poster):
        super().__init__(the_poster)
        self._center = None
        self._radius = None
        self._tile_provider = None

    def create_args(self, args_parser: argparse.ArgumentParser) -> None:
        group = args_parser.add_argument_group("Heatmap Type Options")
        group.add_argument(
            "--heatmap-center",
            dest="heatmap_center",
            metavar="LAT,LNG",
            type=str,
            help="Center of the heatmap (default: automatic).",
        )
        group.add_argument(
            "--heatmap-radius",
            dest="heatmap_radius",
            metavar="RADIUS_KM",
            type=float,
            help="Scale the heatmap such that at least a circle with radius=RADIUS_KM is visible "
            "(default: automatic).",
        )
        group.add_argument(
            "--heatmap-tile-provider",
            dest="heatmap_tile_provider",
            metavar="TILEPROVIDER",
            type=str,
            choices=staticmaps.default_tile_providers.keys(),
            help="Optionally, chose a tile provider from the list for a background map image.",
        )

    def fetch_args(self, args: argparse.Namespace) -> None:
        """Get arguments that were passed, and also perform basic validation on them.

        For example, make sure the center is an actual lat, lng , and make sure the radius is a
        positive number. Also, if radius is passed, then center must also be passed.

        Raises:
            ParameterError: Center was not a valid lat, lng coordinate, or radius was not positive.
        """
        self._center = None
        if args.heatmap_center:
            latlng_str = args.heatmap_center.split(",")
            if len(latlng_str) != 2:
                raise ParameterError(f"Not a valid LAT,LNG pair: {args.heatmap_center}")
            try:
                lat = float(latlng_str[0].strip())
                lng = float(latlng_str[1].strip())
            except ValueError as e:
                raise ParameterError(f"Not a valid LAT,LNG pair: {args.heatmap_center}") from e
            if not -90 <= lat <= 90 or not -180 <= lng <= 180:
                raise ParameterError(f"Not a valid LAT,LNG pair: {args.heatmap_center}")
            self._center = s2sphere.LatLng.from_degrees(lat, lng)
        if args.heatmap_radius:
            if args.heatmap_radius <= 0:
                raise ParameterError(f"Not a valid radius: {args.heatmap_radius} (must be > 0)")
            if not args.heatmap_center:
                raise ParameterError("--heatmap-radius needs --heatmap-center")
            self._radius = args.heatmap_radius
        if args.heatmap_tile_provider:
            self._tile_provider = args.heatmap_tile_provider

    def _determine_bbox(self) -> s2sphere.LatLngRect:
        if self._center:
            log.info("Forcing heatmap center to %s", str(self._center))
            dlat, dlng = 0, 0
            if self._radius:
                er = 6378.1
                quarter = er * math.pi / 2
                dlat = 90 * self._radius / quarter
                scale = 1 / math.cos(self._center.lat().radians)
                dlng = scale * 90 * self._radius / quarter
            else:
                for tr in self.poster.tracks:
                    for line in tr.polylines:
                        for latlng in line:
                            d = abs(self._center.lat().degrees - latlng.lat().degrees)
                            dlat = max(dlat, d)
                            d = abs(self._center.lng().degrees - latlng.lng().degrees)
                            while d > 360:
                                d -= 360
                            if d > 180:
                                d = 360 - d
                            dlng = max(dlng, d)
            return s2sphere.LatLngRect.from_center_size(self._center, s2sphere.LatLng.from_degrees(2 * dlat, 2 * dlng))

        tracks_bbox = s2sphere.LatLngRect()
        for tr in self.poster.tracks:
            tracks_bbox = tracks_bbox.union(tr.bbox())
        return tracks_bbox

    def draw(self, dr: svgwrite.Drawing, g: svgwrite.container.Group, size: XY, offset: XY) -> None:
        """Draw the heatmap based on tracks."""
        bbox = self._determine_bbox()
        year_groups: typing.Dict[int, svgwrite.container.Group] = {}
        for tr in self.poster.tracks:
            year = tr.start_time().year
            if year not in year_groups:
                g_year = dr.g(id=f"year{year}")
                g.add(g_year)
                year_groups[year] = g_year
            else:
                g_year = year_groups[year]
            color = self.color(self.poster.length_range, tr.length(), tr.special)
            for line in utils.project(bbox, size, offset, tr.polylines):
                for opacity, width in [(0.1, 5.0), (0.2, 2.0), (1.0, 0.3)]:
                    g_year.add(
                        dr.polyline(
                            points=line,
                            stroke=color,
                            stroke_opacity=opacity,
                            fill="none",
                            stroke_width=width,
                            stroke_linejoin="round",
                            stroke_linecap="round",
                        )
                    )

    def draw_background(self, dr: svgwrite.Drawing, g: svgwrite.container.Group, size: XY, offset: XY) -> None:
        super().draw_background(dr, g, size, offset)
        if not self._tile_provider:
            return
        # remove padding from poster size to retrieve background image size
        size = size - XY(
            self.poster.padding["l"] + self.poster.padding["r"], self.poster.padding["t"] + self.poster.padding["b"]
        )
        offset = offset + XY(self.poster.padding["l"], self.poster.padding["t"])
        max_width_height = 1024
        bbox = self._determine_bbox()
        if utils.lng2x(bbox.get_size().lng().degrees) > utils.lat2y(bbox.get_size().lat().degrees):
            height = max_width_height
            width = int(height / size.y * size.x)
        else:
            width = max_width_height
            height = int(width / size.x * size.y)

        context = staticmaps.Context()
        context.set_tile_provider(staticmaps.default_tile_providers[self._tile_provider])
        context.set_center(bbox.get_center())
        context.add_bounds(bbox)
        zoom = context.determine_center_zoom(width, height)[1]

        tile_size = staticmaps.default_tile_providers[self._tile_provider].tile_size()
        transformer = staticmaps.Transformer(width, height, zoom, bbox.get_center(), tile_size)
        # render png via pillow
        image = context.render_pillow(width, height)
        # calculate cropping
        lo = transformer.ll2pixel(bbox.lo())
        hi = transformer.ll2pixel(bbox.hi())
        size_x = hi[0] - lo[0]
        size_y = lo[1] - hi[1]
        if width / height > size_x / size_y:
            size_x = width / height * size_y
        else:
            size_y = height / width * size_x
        left = (width - size_x) / 2
        top = (height - size_y) / 2
        right = left + size_x
        bottom = top + size_y
        try:
            tmp_file = str(uuid.uuid4()) + ".png"
            img_res = image.crop((left, top, right, bottom))
            img_res.save(tmp_file)
            with open(tmp_file, "rb") as f:
                img_tmp = f.read()
            img_inl = staticmaps.SvgRenderer.create_inline_image(img_tmp)
            dr.add(dr.image(img_inl, insert=(offset.x, offset.y), size=(size.x, size.y)))
            os.remove(tmp_file)
        except (Image.DecompressionBombError, FileNotFoundError):
            print("Something went wrong!")

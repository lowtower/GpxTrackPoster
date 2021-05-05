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
from typing import Tuple, List

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
        _center: Center of the heatmap.
        _radius: Scale the heatmap so that a circle with radius (in KM) is visible.
        _tile_provider: Tile Provider for background tiles (must comply with py-staticmaps)


    Methods:
        create_args: Create arguments for heatmap.
        fetch_args: Get arguments passed.
        draw: Draw the heatmap based on the Poster's tracks.
        draw_background: Draw the heatmaps background image if requested.
    """

    def __init__(self, the_poster: Poster):
        super().__init__(the_poster)
        self._center = None
        self._radius = None
        self._tile_provider: typing.Optional[staticmaps.TileProvider] = None
        self._tile_context: staticmaps.Context = staticmaps.Context()
        self._bg_max_size: int = 1024
        self._heatmap_line_width: List[Tuple[float, float]] = [(0.1, 5.0), (0.2, 2.0), (1.0, 0.3)]

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
            help="Scale the heatmap such that at least a circle with radius=RADIUS_KM is visible (default: automatic).",
        )
        group.add_argument(
            "--heatmap-tile-provider",
            dest="heatmap_tile_provider",
            metavar="TILE_PROVIDER",
            type=str,
            choices=staticmaps.default_tile_providers.keys(),
            help="Optionally, choose a tile provider from the list for a background map image.",
        )
        group.add_argument(
            "--heatmap-tile-provider",
            dest="heatmap_tile_provider",
            metavar="TILEPROVIDER",
            type=str,
            choices=staticmaps.default_tile_providers.keys(),
            help="Optionally, choose a tile provider from the list for a background map image.",
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
        size, offset = self._get_tracks_width_height_offset(bbox, size, offset)
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
                for opacity, width in self._heatmap_line_width:
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

        # retrieve static map
        bbox = self._determine_bbox()
        self._tile_context.set_tile_provider(staticmaps.default_tile_providers[self._tile_provider])
        self._tile_context.set_center(bbox.get_center())
        self._tile_context.add_bounds(bbox)
        # remove padding from poster size to retrieve background image size
        size = size - XY(
            self.poster.padding["l"] + self.poster.padding["r"], self.poster.padding["t"] + self.poster.padding["b"]
        )
        offset = offset + XY(self.poster.padding["l"], self.poster.padding["t"])
        bg_size = size.scale_to_max_value(self._bg_max_size)

        image = self._tile_context.render_pillow(int(bg_size.x), int(bg_size.y))
        try:
            tmp_file = str(uuid.uuid4()) + ".png"
            image.save(tmp_file)
            with open(tmp_file, "rb") as f:
                img_tmp = f.read()
            img_inl = staticmaps.SvgRenderer.create_inline_image(img_tmp)
            dr.add(dr.image(img_inl, insert=(offset.x, offset.y), size=(size.x, size.y)))
            os.remove(tmp_file)
        except (Image.DecompressionBombError, FileNotFoundError):
            print("Something went wrong generating the background image!")

    def _get_tracks_width_height_offset(self, bbox: s2sphere.LatLngRect, size: XY, offset: XY) -> Tuple[XY, XY]:
        if not self._tile_provider:
            return size, offset

        bg_size = size.scale_to_max_value(self._bg_max_size)
        scale = XY(size.x / bg_size.x, size.y / bg_size.y)
        center, zoom = self._tile_context.determine_center_zoom(int(bg_size.x), int(bg_size.y))
        transformer = staticmaps.Transformer(
            int(bg_size.x),
            int(bg_size.y),
            zoom,
            center,
            staticmaps.default_tile_providers[self._tile_provider].tile_size(),
        )
        tracks_width = math.fabs(transformer.ll2pixel(bbox.hi())[0] - transformer.ll2pixel(bbox.lo())[0])
        tracks_height = math.fabs(transformer.ll2pixel(bbox.hi())[1] - transformer.ll2pixel(bbox.lo())[1])
        tracks_size = XY(int(scale.x * tracks_width), int(scale.y * tracks_height))
        # [(0.1, 5.0), (0.2, 2.0), (1.0, 0.3)]
        stroke = self._heatmap_line_width[0][1]
        tracks_offset_x = stroke + offset.x + scale.x * transformer.ll2pixel(bbox.lo())[0]
        tracks_offset_y = stroke + offset.y + scale.y * transformer.ll2pixel(bbox.hi())[1]
        tracks_offset = XY(int(tracks_offset_x), int(tracks_offset_y))

        return tracks_size, tracks_offset

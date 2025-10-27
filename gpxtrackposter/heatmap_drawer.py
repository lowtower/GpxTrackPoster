"""Draw a heatmap poster."""

# Copyright 2016-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from __future__ import annotations

import logging
import math
import os
import sys
import uuid
from operator import itemgetter
from typing import TYPE_CHECKING

import s2sphere  # type: ignore[attr-defined]
import staticmaps  # type: ignore[attr-defined]
from geopy.distance import distance  # type: ignore[attr-defined]
from PIL import Image  # type: ignore[attr-defined]

from gpxtrackposter import utils
from gpxtrackposter.exceptions import ParameterError, PosterError
from gpxtrackposter.tracks_drawer import TracksDrawer
from gpxtrackposter.xy import XY

if TYPE_CHECKING:
    import argparse

    import svgwrite  # type: ignore[attr-defined]

    from gpxtrackposter.poster import Poster

log = logging.getLogger("gpxtrackposter")


class HeatmapDrawer(TracksDrawer):
    """Draw a heatmap Poster based on the tracks.

    Attributes:
        _center: Center of the heatmap.
        _radius: Scale the heatmap so that a circle with radius (in KM) is visible.
        _heatmap_line_width_low: Heatmap line width lower border for automatic calculation of line widths.
        _heatmap_line_width_upp: Heatmap line width upper border for automatic calculation of line widths.
        _heatmap_line_width_lower: List of Tuples with line transparency and width for lower border.
        _heatmap_line_width_upper: List of Tuples with line transparency and width for higher border.
        _heatmap_line_width: List of Tuples with line transparency and width.

    Methods:
        create_args: Create arguments for heatmap.
        fetch_args: Get arguments passed.
        draw: Draw the heatmap based on the Poster's tracks.
        draw_background: Draw the heatmaps background image if requested.

    """

    def __init__(self, the_poster: Poster) -> None:
        """Initialize the HeatmapDrawer class."""
        super().__init__(the_poster)
        self._center: s2sphere.LatLng | None = None
        self._radius: float | None = None
        self._heatmap_line_width_low: float = 10.0
        self._heatmap_line_width_upp: float = 1000.0
        self._heatmap_line_width_lower: list[tuple[float, float]] = [(0.10, 5.0), (0.20, 2.0), (1.0, 0.30)]
        self._heatmap_line_width_upper: list[tuple[float, float]] = [(0.02, 0.5), (0.05, 0.2), (1.0, 0.05)]
        self._heatmap_line_width: list[tuple[float, float]] | None = None
        self._heatmap_renderer: str = "pillow"
        self._tile_provider: staticmaps.TileProvider | None = None
        self._tile_context: staticmaps.Context = staticmaps.Context()
        self._bg_max_size: int = 1200
        self._transformer: staticmaps.Transformer | None = None

    def create_args(self, args_parser: argparse.ArgumentParser) -> None:
        """Add arguments to the parser

        Args:
            args_parser: ArgumentParser

        """
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
            "--heatmap-line-transparency-width",
            dest="heatmap_line_width",
            metavar="TRANSP_1,WIDTH_1, TRANSP_2,WIDTH_2, TRANSP_3,WIDTH_3",
            type=str,
            help="Define three transparency and width tuples for the heatmap lines or set it to "
            "`automatic` for automatic calculation (default: 0.1,5.0, 0.2,2.0, 1.0,0.3).",
        )
        tile_provider = staticmaps.default_tile_providers.keys()
        group.add_argument(
            "--heatmap-tile-provider",
            dest="heatmap_tile_provider",
            metavar="TILE_PROVIDER",
            type=str,
            choices=tile_provider,
            help="Optionally, choose a tile provider from the list for a background map image: "
            f"{', '.join(tile_provider)}. (Default: None)",
        )
        group.add_argument(
            "--heatmap-tile-max-size",
            dest="heatmap_tile_max_size",
            metavar="PIXEL",
            type=int,
            default=1200,
            help="Set the maximum background image size (which is afterwards scaled to the poster size). "
            "This setting defines how much details will be shown on the map. "
            "Be sure to choose a reasonable value! (default: 1200 px)",
        )
        bg_renderer = ["pillow", "cairo"]
        group.add_argument(
            "--heatmap-tile-renderer",
            dest="heatmap_renderer",
            metavar="RENDERER",
            choices=bg_renderer,
            default=self._heatmap_renderer,
            help=f"Choose a renderer for generating the background image, one of {', '.join(bg_renderer)}. "
            f"(default: {self._heatmap_renderer})",
        )

    def fetch_args(self, args: argparse.Namespace) -> None:
        """Get arguments that were passed, and also perform basic validation on them.

        For example, make sure the center is an actual lat, lng , and make sure the radius is a
        positive number. Also, if radius is passed, then center must also be passed.

        Args:
            args: Namespace

        """
        self._center = self.validate_heatmap_center(args.heatmap_center)
        self._radius = self.validate_heatmap_radius(args.heatmap_radius)
        self._heatmap_line_width = self.validate_heatmap_line_width(args.heatmap_line_width)
        self._center = self.validate_heatmap_center(args.heatmap_center)
        self._radius = self.validate_heatmap_radius(args.heatmap_radius)
        self._heatmap_line_width = self.validate_heatmap_line_width(args.heatmap_line_width)

        if args.heatmap_tile_provider:
            self._tile_provider = args.heatmap_tile_provider
        if args.heatmap_tile_max_size:
            self._bg_max_size = args.heatmap_tile_max_size
            if args.heatmap_tile_max_size > 4800:
                msg = (
                    f"A size of < {args.heatmap_tile_max_size} > pixels for the background image is very high.\n"
                    "Fetching large tiles takes time and consumes much disk space.\n"
                    "Consider choosing a smaller size!"
                )
                log.warning(msg)
        # set background image renderer
        self._heatmap_renderer = args.heatmap_renderer

    def get_line_transparencies_and_widths(self, bbox: s2sphere.sphere.LatLngRect) -> list[tuple[float, float]]:
        """Get a list of tuples of line widths and transparencies

        Args:
            bbox: Boundary box for automatic calculation of line transparencies and widths

        Returns:
            list: List of tuples of line transparencies and widths

        """
        if self._heatmap_line_width:
            return self._heatmap_line_width
        # automatic calculation of line transparencies and widths
        low = self._heatmap_line_width_low
        upp = self._heatmap_line_width_upp
        lower = self._heatmap_line_width_lower
        upper = self._heatmap_line_width_upper
        d = distance(
            (bbox.lo().lat().degrees, bbox.lo().lng().degrees), (bbox.hi().lat().degrees, bbox.hi().lng().degrees)
        ).km
        log.info("Length of diagonal of boundary box %s", str(d))
        if d > upp:
            return upper
        if d < low:
            return lower
        return [
            (
                lower[0][0] + d / (upp - low) * (upper[0][0] - lower[0][0]),
                (lower[0][1] + d / (upp - low) * (upper[0][1] - lower[0][1])),
            ),
            (
                lower[1][0] + d / (upp - low) * (upper[1][0] - lower[1][0]),
                (lower[1][1] + d / (upp - low) * (upper[1][1] - lower[1][1])),
            ),
            (
                lower[2][0] + d / (upp - low) * (upper[2][0] - lower[2][0]),
                (lower[2][1] + d / (upp - low) * (upper[2][1] - lower[2][1])),
            ),
        ]

    def _determine_bbox(self) -> s2sphere.LatLngRect:
        if self._center:
            log.info("Forcing heatmap center to %s", str(self._center))
            dlat, dlng = 0.0, 0.0
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
        """Draw the heatmap based on tracks.

        Args:
            dr: svg drawing
            g: svg group
            size: Size
            offset: Offset

        """
        if len(self.poster.tracks) == 0:
            msg = "No tracks to draw."
            raise PosterError(msg)
        bbox = self._determine_bbox()
        size, offset = self._get_tracks_size_offset(bbox, size, offset)
        line_transparencies_and_widths = self.get_line_transparencies_and_widths(bbox)
        year_groups: dict[int, svgwrite.container.Group] = {}
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
                for opacity, width in line_transparencies_and_widths:
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

    def validate_heatmap_center(self, heatmap_center: str | None = None) -> s2sphere.LatLng:
        """Validate and return the Heatmap center.

        Args:
            heatmap_center: Heatmap center

        Raises:
            ParameterError: Center was not a valid lat, lng coordinate, or radius was not positive.
            ParameterError: Line transparency and width values are not valid.

        """
        if heatmap_center:
            latlng_str = heatmap_center.split(",")
            if len(latlng_str) != 2:
                msg = f"Not a valid LAT,LNG pair: {heatmap_center}"
                raise ParameterError(msg)
            try:
                lat = float(latlng_str[0].strip())
                lng = float(latlng_str[1].strip())
            except ValueError as e:
                msg = f"Not a valid LAT,LNG pair: {heatmap_center}"
                raise ParameterError(msg) from e
            if not -90 <= lat <= 90 or not -180 <= lng <= 180:
                msg = f"Not a valid LAT,LNG pair: {heatmap_center}"
                raise ParameterError(msg)
            self._center = s2sphere.LatLng.from_degrees(lat, lng)
        return self._center

    def validate_heatmap_radius(self, heatmap_radius: float | None = None) -> float | None:
        """Validate and return the Heatmap radius.

        Args:
            heatmap_radius: Heatmap radius

        Returns:
            float: Validated heatmap radius

        Raises:
            ParameterError: Radius was not valid.
            ParameterError: Heatmap center is missing.

        """
        if heatmap_radius:
            if heatmap_radius <= 0:
                msg = f"Not a valid radius: {heatmap_radius} (must be > 0)"
                raise ParameterError(msg)
            if not self._center:
                msg = "--heatmap-radius needs --heatmap-center"
                raise ParameterError(msg)
            self._radius = heatmap_radius
        return self._radius

    def validate_heatmap_line_width(self, heatmap_line_width: str | None = None) -> list[tuple[float, float]] | None:
        """Validate and return a tuple of the Heatmap line widths.

        Args:
            heatmap_line_width: Heatmap line width

        Returns:
            list: List of tuples of line widths

        Raises:
            ParameterError: Not three valid TRANSPARENCY,WIDTH pairs.
            ParameterError: Not a valid TRANSPARENCY value.

        """
        if heatmap_line_width:
            if heatmap_line_width.lower() == "automatic":
                self._heatmap_line_width = None
            else:
                trans_width_str = heatmap_line_width.split(",")
                if len(trans_width_str) != 6:
                    msg = f"Not three valid TRANSPARENCY,WIDTH pairs: {heatmap_line_width}"
                    raise ParameterError(msg)
                try:
                    self._heatmap_line_width = []
                    for value in range(0, 5, 2):
                        transparency = float(trans_width_str[value].strip())
                        width = float(trans_width_str[value + 1].strip())
                        if transparency < 0 or transparency > 1:
                            msg = (
                                f"Not a valid TRANSPARENCY value (0 < value < 1): "
                                f"{transparency} in {heatmap_line_width}"
                            )
                            raise ParameterError(msg)
                        self._heatmap_line_width.append((transparency, width))
                except ValueError as e:
                    msg = f"Not three valid TRANSPARENCY,WIDTH pairs: {heatmap_line_width}"
                    raise ParameterError(msg) from e
            return self._heatmap_line_width
        return None

    def draw_background(self, dr: svgwrite.Drawing, g: svgwrite.container.Group, size: XY, offset: XY) -> None:
        """Draw background with background static map if requested

        Args:
            dr: svg drawing
            g: svg group
            size: Size
            offset: Offset

        """
        super().draw_background(dr, g, size, offset)
        if not self._tile_provider:
            return

        # retrieve static map
        bbox = self._determine_bbox()
        self._tile_context.set_tile_provider(staticmaps.default_tile_providers[self._tile_provider])
        self._tile_context.set_center(bbox.get_center())
        # remove padding from poster size to retrieve background image size
        size = size - XY(
            self.poster.padding["l"] + self.poster.padding["r"], self.poster.padding["t"] + self.poster.padding["b"]
        )
        offset = offset + XY(self.poster.padding["l"], self.poster.padding["t"])
        bg_size = size.scale_to_max_value(self._bg_max_size).round()

        # get maximum track line width, scale and add to background image boundary
        scale = max([bg_size.x / size.x, bg_size.y / size.y])
        self._heatmap_line_width = self.get_line_transparencies_and_widths(bbox)
        half_stroke = round(scale * (max(self._heatmap_line_width, key=itemgetter(1))[1] / 2))
        bbox_corner_list = [bbox.get_vertex(0), bbox.get_vertex(1), bbox.get_vertex(2), bbox.get_vertex(3)]
        bounds = staticmaps.Bounds(bbox_corner_list, half_stroke)
        self._tile_context.add_object(bounds)
        # tighten the background map to bounds
        self._tile_context.set_tighten_to_bounds(True)

        # set transformer with center and zoom
        center, zoom = self._tile_context.determine_center_zoom(bg_size.x, bg_size.y)
        self._transformer = staticmaps.Transformer(
            bg_size.x,
            bg_size.y,
            zoom,
            center,
            staticmaps.default_tile_providers[self._tile_provider].tile_size(),
        )

        # TODO: remove testing code
        from staticmaps.color import BLACK, RED  # type: ignore[attr-defined]

        self._tile_context.add_object(staticmaps.Line([bbox.lo(), bbox.hi()], RED, 1))
        self._tile_context.add_object(
            staticmaps.Line(
                [
                    s2sphere.LatLng.from_angles(bbox.lat_lo(), bbox.lng_lo()),
                    s2sphere.LatLng.from_angles(bbox.lat_lo(), bbox.lng_hi()),
                    s2sphere.LatLng.from_angles(bbox.lat_hi(), bbox.lng_hi()),
                    s2sphere.LatLng.from_angles(bbox.lat_hi(), bbox.lng_lo()),
                    s2sphere.LatLng.from_angles(bbox.lat_lo(), bbox.lng_lo()),
                ],
                BLACK,
                1,
            )
        )

        try:
            # generate a unique filename
            tmp_file = f"{uuid.uuid4()}.png"

            # render background image based on command line argument
            if self._heatmap_renderer == "cairo":
                try:
                    __import__("cairo")
                except ImportError:
                    msg = (
                        "The cairo module cannot be imported. "
                        "Please consider choosing 'pillow' as background image renderer instead!"
                    )
                    sys.exit(msg)
                image = self._tile_context.render_cairo(bg_size.x, bg_size.y)
                image.write_to_png(tmp_file)
            else:
                image = self._tile_context.render_pillow(bg_size.x, bg_size.y)
                image.save(tmp_file)
            with open(tmp_file, "rb") as f:
                img_inl = staticmaps.SvgRenderer.create_inline_image(f.read())
                dr.add(dr.image(img_inl, insert=(offset.x, offset.y), size=(size.x, size.y)))
            os.remove(tmp_file)
        except (Image.DecompressionBombError, FileNotFoundError):
            log.info("Something went wrong generating the background image!")

    def _get_tracks_size_offset(self, bbox: s2sphere.LatLngRect, size: XY, offset: XY) -> tuple[XY, XY]:
        if not self._tile_provider:
            return size, offset

        # background image size
        bg_size = size.scale_to_max_value(self._bg_max_size)
        tracks_scale = size / bg_size

        transformer = self._transformer
        assert transformer is not None
        tracks_width = math.fabs(transformer.ll2pixel(bbox.hi())[0] - transformer.ll2pixel(bbox.lo())[0])
        tracks_height = math.fabs(transformer.ll2pixel(bbox.hi())[1] - transformer.ll2pixel(bbox.lo())[1])
        # add maximum track line width
        assert self._heatmap_line_width
        max_stroke = max(self._heatmap_line_width, key=itemgetter(1))[1]
        half_stroke = max_stroke / 2
        tracks_size = XY(tracks_width, tracks_height) + max_stroke
        tracks_size_scaled = tracks_scale * tracks_size
        tracks_offset = offset + tracks_scale * (
            XY(math.fabs(transformer.ll2pixel(bbox.lo())[0]), math.fabs(transformer.ll2pixel(bbox.hi())[1]))
            - half_stroke
        )
        return tracks_size_scaled, tracks_offset

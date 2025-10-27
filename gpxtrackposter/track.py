"""Create and maintain info about a given activity track (corresponding to one GPX file)."""

# Copyright 2016-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from __future__ import annotations

import datetime
import json
import os
from typing import TYPE_CHECKING

import gpxpy  # type: ignore[import-untyped]
import polyline  # type: ignore[import-untyped]
import s2sphere  # type: ignore[import-untyped]

from gpxtrackposter.exceptions import TrackLoadError
from gpxtrackposter.units import Units

if TYPE_CHECKING:
    import pint  # type: ignore[import-untyped]
    from stravalib.model import (
        SummaryActivity as StravaActivity,  # type: ignore[import-untyped]
    )

    from gpxtrackposter.timezone_adjuster import TimezoneAdjuster


class Track:
    """Create and maintain info about a given activity track (corresponding to one GPX file).

    Attributes:
        file_names: Basename of a given file passed in load_gpx.
        polylines: Lines interpolated between each coordinate.
        _start_time: Activity start time.
        _end_time: Activity end time.
        _length_meters: Length of the track (2-dimensional).
        special: True if track is special, else False.
        activity_type: Activity type

    Methods:
        load_gpx: Load a GPX file into the current track.
        bbox: Compute the border box of the track.
        append: Append other track to current track.
        load_cache: Load track from cached json data.
        store_cache: Cache the current track.

    """

    def __init__(self) -> None:
        """Initialize the Track class."""
        self.file_names: list[str] = []
        self.polylines: list[list[s2sphere.LatLng]] = []
        self._start_time: datetime.datetime | None = None
        self._end_time: datetime.datetime | None = None
        # Don't use Units().meter here, as this constructor is called from
        # within a thread (which would create a second unit registry!)
        self._length_meters = 0.0
        self.special = False
        self.activity_type = None

    def load_gpx(self, file_name: str, timezone_adjuster: TimezoneAdjuster | None) -> None:
        """Load the GPX file into self.

        Args:
            file_name: GPX file to be loaded.
            timezone_adjuster: timezone adjuster

        Raises:
            TrackLoadError: An error occurred while parsing the GPX file (empty or bad format).
            PermissionError: An error occurred while opening the GPX file.

        """
        try:
            self.file_names = [os.path.basename(file_name)]
            # Handle empty gpx files
            # (for example, treadmill runs pulled via garmin-connect-export)
            if os.path.getsize(file_name) == 0:
                msg = "Empty GPX file"
                raise TrackLoadError(msg)
            with open(file_name, encoding="utf8") as file:
                self._load_gpx_data(gpxpy.parse(file), timezone_adjuster)
        except TrackLoadError:
            raise
        except gpxpy.gpx.GPXXMLSyntaxException as e:
            msg = "Failed to parse GPX."
            raise TrackLoadError(msg) from e
        except PermissionError as e:
            msg = "Cannot load GPX (bad permissions)"
            raise TrackLoadError(msg) from e
        except Exception as e:
            msg = "Something went wrong when loading GPX."
            raise TrackLoadError(msg) from e

    def load_strava(self, activity: StravaActivity) -> None:
        """Load Strava activity into self.

        Args:
            activity: Strava activity

        """
        # use strava as file name
        self.file_names = [str(activity.id)]
        if not activity.start_date_local or not activity.distance or not activity.map or not activity.elapsed_time:
            msg = "Strava activity is not valid!"
            raise ValueError(msg)
        self.set_start_time(activity.start_date_local)
        self.set_end_time(activity.start_date_local + activity.elapsed_time.timedelta())
        self._length_meters = float(activity.distance)
        summary_polyline = activity.map.summary_polyline
        polyline_data = polyline.decode(summary_polyline) if summary_polyline else []
        self.polylines = [[s2sphere.LatLng.from_degrees(p[0], p[1]) for p in polyline_data]]

    def has_time(self) -> bool:
        """Check whether the track has at least one time, either start or end time.

        Returns:
            bool: True if track has at least one time, either start or end time.

        """
        return self._start_time is not None and self._end_time is not None

    def start_time(self) -> datetime.datetime:
        """Return the start time.

        Returns:
            datetime.datetime: The start time.

        """
        assert self._start_time is not None
        return self._start_time

    def set_start_time(self, value: datetime.datetime | None) -> None:
        """Set the start time to the given value.

        Args:
            value: The start time value.

        """
        self._start_time = value

    def end_time(self) -> datetime.datetime:
        """Return the end time.

        Returns:
            datetime.datetime: The end time.

        """
        assert self._end_time is not None
        return self._end_time

    def set_end_time(self, value: datetime.datetime) -> None:
        """Set the end time to the given value.

        Args:
            value: The end time value.

        """
        self._end_time = value

    @property
    def length_meters(self) -> float:
        """Return the track length in meters.

        Returns:
            float: The track length in meters.

        """
        return self._length_meters

    @length_meters.setter
    def length_meters(self, value: float) -> None:
        """Set the track length in meters to the given value.

        Args:
            value: The track length in meters.

        """
        self._length_meters = value

    def length(self) -> pint.Quantity:
        """Return the track length.

        Returns:
            pint.Quantity: The track length.

        """
        return self._length_meters * Units().meter

    def bbox(self) -> s2sphere.LatLngRect:
        """Compute the smallest rectangle that contains the entire track (border box).

        Returns:
            s2sphere.LatLngRect: The smallest rectangle that contains the entire track (border box).

        """
        bbox = s2sphere.LatLngRect()
        for line in self.polylines:
            for latlng in line:
                bbox = bbox.union(s2sphere.LatLngRect.from_point(latlng.normalized()))
        return bbox

    def _load_gpx_data(self, gpx: gpxpy.gpx.GPX, timezone_adjuster: TimezoneAdjuster | None) -> None:
        self._start_time, self._end_time = gpx.get_time_bounds()
        if not self.has_time():
            msg = "Track has no start or end time."
            raise TrackLoadError(msg)
        if timezone_adjuster:
            lat, _, lng, _ = list(gpx.get_bounds())  # type: ignore[import-untyped]
            latlng = s2sphere.LatLng.from_degrees(lat, lng)
            self.set_start_time(timezone_adjuster.adjust(self.start_time(), latlng))
            self.set_end_time(timezone_adjuster.adjust(self.end_time(), latlng))
        self._length_meters = gpx.length_2d()
        if self._length_meters <= 0:
            msg = "Track is empty."
            raise TrackLoadError(msg)
        gpx.simplify()
        for t in gpx.tracks:
            for s in t.segments:
                line = [s2sphere.LatLng.from_degrees(p.latitude, p.longitude) for p in s.points]
                self.polylines.append(line)
        if gpx.tracks[0].type:
            self.activity_type = gpx.tracks[0].type.lower()

    def append(self, other: Track) -> None:
        """Append other track to self.

        Args:
            other: Other track to append.

        """
        self._end_time = other.end_time()
        self.polylines.extend(other.polylines)
        self._length_meters += other.length_meters
        self.file_names.extend(other.file_names)
        self.special = self.special or other.special

    def load_cache(self, cache_file_name: str) -> None:
        """Load the track from a previously cached track

        Args:
            cache_file_name: Filename of the cached track to be loaded.

        Raises:
            TrackLoadError: An error occurred while loading the track data from the cache file.

        """
        try:
            with open(cache_file_name, encoding="utf8") as data_file:
                data = json.load(data_file)
                self.set_start_time(datetime.datetime.strptime(data["start"], "%Y-%m-%d %H:%M:%S"))
                self.set_end_time(datetime.datetime.strptime(data["end"], "%Y-%m-%d %H:%M:%S"))
                self._length_meters = float(data["length"])
                self.polylines = []
                for data_line in data["segments"]:
                    self.polylines.append(
                        [s2sphere.LatLng.from_degrees(float(d["lat"]), float(d["lng"])) for d in data_line]
                    )
        except Exception as e:
            msg = "Failed to load track data from cache."
            raise TrackLoadError(msg) from e

    def store_cache(self, cache_file_name: str) -> None:
        """Cache the current track.

        Args:
            cache_file_name: The name of the cache file.

        """
        dir_name = os.path.dirname(cache_file_name)
        if not os.path.isdir(dir_name):
            os.makedirs(dir_name)
        with open(cache_file_name, "w", encoding="utf8") as json_file:
            lines_data = [
                [{"lat": latlng.lat().degrees, "lng": latlng.lng().degrees} for latlng in line]
                for line in self.polylines
            ]
            json.dump(
                {
                    "start": self.start_time().strftime("%Y-%m-%d %H:%M:%S"),
                    "end": self.end_time().strftime("%Y-%m-%d %H:%M:%S"),
                    "length": self._length_meters,
                    "segments": lines_data,
                },
                json_file,
            )

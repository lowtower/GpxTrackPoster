"""Several tests for Track"""

# Copyright 2022-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import datetime
import os
import re

import pytest
import s2sphere  # type: ignore[import-untyped]
from pint import Quantity  # type: ignore[import-untyped]

from gpxtrackposter.exceptions import TrackLoadError
from gpxtrackposter.track import Track
from gpxtrackposter.units import Units


def test_init() -> None:
    """Test init function"""
    track = Track()
    assert len(track.file_names) == 0
    assert len(track.polylines) == 0
    assert not track.special
    assert not track.activity_type
    assert not track.has_time()
    assert track.length_meters == 0.0
    assert 0.0 * Units().meter == track.length()


def test_set_start_time() -> None:
    """Test set_start_time function"""
    track = Track()
    start_time = datetime.datetime(2022, 1, 1, 1, 1, 1)
    track.set_start_time(start_time)
    assert start_time == track.start_time()
    assert not track.has_time()


def test_set_end_time() -> None:
    """Test set_end_time function"""
    track = Track()
    end_time = datetime.datetime(2022, 2, 2, 2, 2, 2)
    track.set_end_time(end_time)
    assert end_time == track.end_time()
    assert not track.has_time()


def test_set_start_and_end_time() -> None:
    """Test set_start_time and set_end_time function"""
    track = Track()
    start_time = datetime.datetime(2022, 1, 1, 1, 1, 1)
    end_time = datetime.datetime(2022, 2, 2, 2, 2, 2)
    assert not track.has_time()
    track.set_start_time(start_time)
    track.set_end_time(end_time)
    assert track.has_time()


def test_length_meters() -> None:
    """Test length function"""
    track = Track()
    assert track.length_meters == 0.0
    track.length_meters = 1234.5
    assert track.length_meters == 1234.5
    assert Quantity(1234.5, "meter") == track.length()


def test_load_gpx_file_does_not_exist() -> None:
    """Test load gpx file does not exist"""
    track = Track()
    test_dir = "this_dir_does_not_exist/this_file_does_not_exist.gpx"
    assert not os.path.isdir(test_dir)
    with pytest.raises(TrackLoadError, match=re.escape("Something went wrong when loading GPX.")):
        track.load_gpx(test_dir, None)


def test_load_gpx_empty_file(gpx_file_empty: str) -> None:
    """Test load gpx file with empty gpx file"""
    track = Track()
    with pytest.raises(TrackLoadError, match="Empty GPX file"):
        track.load_gpx(gpx_file_empty, None)


def test_load_gpx_invalid_file(gpx_file_invalid: str) -> None:
    """Test load gpx file with invalid gpx file"""
    track = Track()
    with pytest.raises(TrackLoadError, match=re.escape("Failed to parse GPX.")):
        track.load_gpx(gpx_file_invalid, None)


def test_load_gpx_no_permission(gpx_file_no_permission: str) -> None:
    """Test load gpx file with no permission"""
    track = Track()
    with pytest.raises(TrackLoadError, match=re.escape("Cannot load GPX (bad permissions)")):
        track.load_gpx(gpx_file_no_permission, None)


def test_load_gpx_no_length(gpx_file_track_no_length: str) -> None:
    """Test load gpx file with no length"""
    track = Track()
    with pytest.raises(TrackLoadError, match=re.escape("Track is empty.")):
        track.load_gpx(gpx_file_track_no_length, None)


def test_load_gpx_valid_file_walk(gpx_file_track_walk: str) -> None:
    """Test load gpx file with valid gpx file of type walk"""
    track = Track()
    assert len(track.polylines) == 0
    track.load_gpx(gpx_file_track_walk, None)
    assert len(track.polylines) != 0
    assert track.has_time()
    assert track.activity_type == "walk"


def test_load_gpx_valid_file_no_type(gpx_file_track_no_type: str) -> None:
    """Test load gpx file with valid gpx file but no type"""
    track = Track()
    assert len(track.polylines) == 0
    track.load_gpx(gpx_file_track_no_type, None)
    assert len(track.polylines) != 0
    assert track.has_time()
    assert not track.activity_type


def test_load_gpx_valid_file_append(gpx_file_track_walk: str, gpx_file_track_no_type: str) -> None:
    """Test load gpx file with valid gpx file append"""
    track = Track()
    track2 = Track()
    track.load_gpx(gpx_file_track_walk, None)
    length_before = track.length()
    track2.load_gpx(gpx_file_track_no_type, None)
    track.append(track2)
    assert track.length() > length_before


def test_bbox(gpx_file_track_walk: str) -> None:
    """Test bbox function"""
    track = Track()
    track.load_gpx(gpx_file_track_walk, None)
    assert track.bbox() == s2sphere.sphere.LatLngRect.from_point_pair(
        s2sphere.LatLng.from_degrees(52.516495, 13.377094),
        s2sphere.LatLng.from_degrees(52.517959, 13.380634),
    )

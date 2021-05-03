# Copyright 2018-2021 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from datetime import datetime
from gpxtrackposter.utils import interpolate_color, get_time_in_seconds, get_clock_angle_from_time


def test_interpolate_color() -> None:
    assert interpolate_color("#000000", "#ffffff", 0) == "#000000"
    assert interpolate_color("#000000", "#ffffff", 1) == "#ffffff"
    assert interpolate_color("#000000", "#ffffff", 0.5) == "#7f7f7f"
    assert interpolate_color("#000000", "#ffffff", -100) == "#000000"
    assert interpolate_color("#000000", "#ffffff", 12345) == "#ffffff"


def test_get_time_in_seconds() -> None:
    test_times = [
        ("0:00:00", 0),
        ("12:00:00", 0),
        ("3:00:00", 10800),
        ("15:00:00", 10800),
        ("6:00:00", 21600),
        ("18:00:00", 21600),
        ("9:00:00", 32400),
        ("21:00:00", 32400),
    ]
    for time_inp, result in test_times:
        time_obj = datetime.strptime(time_inp, "%H:%M:%S").time()
        assert get_time_in_seconds(time_obj) == result


def test_get_clock_angle_from_time() -> None:
    test_times = [
        ("0:00:00", 0.0),
        ("12:00:00", 0.0),
        ("3:00:00", 90.0),
        ("15:00:00", 90.0),
        ("6:00:00", 180.0),
        ("18:00:00", 180.0),
        ("9:00:00", 270.0),
        ("21:00:00", 270.0),
    ]
    for time_inp, result in test_times:
        time_obj = datetime.strptime(time_inp, "%H:%M:%S").time()
        assert get_clock_angle_from_time(time_obj) == result

# Copyright 2021-2021 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from gpxtrackposter.xy import XY


def test_multiplication() -> None:
    test_object = XY(50.0, 100.0)
    test_values = [
        (10.0, XY(500.0, 1000.0)),
        (10, XY(500.0, 1000.0)),
        (0.5, XY(25.0, 50.0)),
        (-5.0, XY(-250.0, -500.0)),
        (XY(10.0, 5.0), XY(500.0, 500.0)),
        (XY(-10.0, 5.0), XY(-500.0, 500.0)),
        (XY(0.5, -5.0), XY(25.0, -500.0)),
    ]
    for test_value in test_values:
        other, result = test_value
        assert (test_object * other).tuple() == result.tuple()


def test_addition() -> None:
    test_object = XY(50.0, 100.0)
    test_values = [
        (10.0, XY(60.0, 110.0)),
        (10, XY(60.0, 110.0)),
        (0.5, XY(50.5, 100.5)),
        (-5.0, XY(45.0, 95.0)),
        (XY(10.0, 5.0), XY(60.0, 105.0)),
        (XY(-10.0, 5.0), XY(40.0, 105.0)),
        (XY(0.5, -5.0), XY(50.5, 95.0)),
    ]
    for test_value in test_values:
        other, result = test_value
        assert (test_object + other).tuple() == result.tuple()


def test_subtraction() -> None:
    test_object = XY(50.0, 100.0)
    test_values = [
        (10.0, XY(40.0, 90.0)),
        (10, XY(40.0, 90.0)),
        (0.5, XY(49.5, 99.5)),
        (-5.0, XY(55.0, 105.0)),
        (XY(10.0, 5.0), XY(40.0, 95.0)),
        (XY(-10.0, 5.0), XY(60.0, 95.0)),
        (XY(0.5, -5.0), XY(49.5, 105.0)),
    ]
    for test_value in test_values:
        other, result = test_value
        assert (test_object - other).tuple() == result.tuple()


def test_representation() -> None:
    test_object = XY(50.0, 100.0)
    assert str(test_object) == "XY: 50.0/100.0"


def test_tuple() -> None:
    test_object = XY(50.0, 100.0)
    assert test_object.tuple() == (50.0, 100.0)


def test_scale_to_max_value() -> None:
    test_object = XY(50.0, 100.0)
    good_values = [
        (25.0, XY(12.5, 25.0)),
        (50.0, XY(25.0, 50.0)),
        (200.0, XY(100.0, 200.0)),
        (-50.0, XY(-25.0, -50.0)),
    ]
    bad_values = [
        (25.0, XY(25.0, 12.5)),
        (-50.0, XY(25.0, -50.0)),
        (-50.0, XY(-25.0, 50.0)),
    ]
    for good_value in good_values:
        max_value, result = good_value
        assert test_object.scale_to_max_value(max_value).tuple() == result.tuple()

    for bad_value in bad_values:
        max_value, result = bad_value
        assert test_object.scale_to_max_value(max_value).tuple() != result.tuple()

"""Unit tests for audiogram aggregation."""

import json

import pytest

from audiometer.audiogram import (
    PTA_FREQUENCIES,
    build_audiogram,
    classification_for,
    ears_match,
    pta_for,
    thresholds_for,
    to_dict,
    to_json_string,
)
from audiometer.types import Audiogram, AudiogramPoint, Ear, Just, Nothing


def _full_left():
    return [
        AudiogramPoint(Ear.LEFT, 500, 10),
        AudiogramPoint(Ear.LEFT, 1000, 20),
        AudiogramPoint(Ear.LEFT, 2000, 30),
        AudiogramPoint(Ear.LEFT, 4000, 40),
    ]


def _full_right():
    return [
        AudiogramPoint(Ear.RIGHT, 500, 5),
        AudiogramPoint(Ear.RIGHT, 1000, 15),
        AudiogramPoint(Ear.RIGHT, 2000, 25),
        AudiogramPoint(Ear.RIGHT, 4000, 35),
    ]


def test_build_audiogram_is_immutable():
    pts = _full_left()
    ag = build_audiogram(pts)
    assert isinstance(ag.points, tuple)
    pts.append(AudiogramPoint(Ear.LEFT, 8000, 50))
    assert len(ag.points) == 4  # unaffected


def test_thresholds_for_ear_returns_dict():
    ag = build_audiogram(_full_left() + _full_right())
    left = thresholds_for(ag, Ear.LEFT)
    assert left == {500: 10, 1000: 20, 2000: 30, 4000: 40}


def test_pta_for_returns_mean_when_all_present():
    ag = build_audiogram(_full_left())
    assert pta_for(ag, Ear.LEFT) == Just(25.0)


def test_pta_for_returns_nothing_when_incomplete():
    ag = build_audiogram([AudiogramPoint(Ear.LEFT, 500, 10)])
    assert pta_for(ag, Ear.LEFT) == Nothing()


def test_classification_for_uses_who_grades():
    ag = build_audiogram(_full_left())  # PTA = 25 -> Normal
    cls = classification_for(ag, Ear.LEFT)
    assert cls == Just("Normal")


def test_ears_match_within_tolerance():
    ag = build_audiogram(_full_left() + _full_right())
    assert ears_match(ag, tolerance_db=10) == Just(True)


def test_ears_match_requires_both_ears():
    ag = build_audiogram(_full_left())
    assert ears_match(ag) == Nothing()


def test_to_dict_round_trips_through_json():
    ag = build_audiogram(_full_left() + _full_right())
    s = to_json_string(ag)
    decoded = json.loads(s)
    assert decoded == to_dict(ag)
    assert len(decoded["points"]) == 8


def test_pta_uses_required_frequencies():
    assert PTA_FREQUENCIES == (500, 1000, 2000, 4000)

"""Unit tests for IEC 60645-1 conformance validators."""

import pytest

from audiometer.audiogram import build_audiogram
from audiometer.hughson_westlake import run_session
from audiometer.iec60645 import (
    REQUIRED_DIAGNOSTIC_FREQUENCIES,
    REQUIRED_SCREENING_FREQUENCIES,
    audiogram_complete,
    state_is_iec_conformant,
    step_sizes_correct,
    validate_audiogram_point,
    validate_stimulus,
)
from audiometer.types import (
    Audiogram,
    AudiogramPoint,
    Ear,
    Err,
    Ok,
    Presentation,
    Stimulus,
)


# ---------------------------------------------------------------------------
# Stimulus / point validation
# ---------------------------------------------------------------------------


def test_valid_stimulus_passes():
    s = Stimulus(frequency_hz=1000, level_db=40, ear=Ear.RIGHT)
    assert isinstance(validate_stimulus(s), Ok)


def test_invalid_frequency_rejected():
    s = Stimulus(frequency_hz=333, level_db=40, ear=Ear.RIGHT)
    result = validate_stimulus(s)
    assert isinstance(result, Err)
    assert any("frequency" in msg for msg in result.error)


def test_invalid_db_rejected():
    s = Stimulus(frequency_hz=1000, level_db=200, ear=Ear.RIGHT)
    result = validate_stimulus(s)
    assert isinstance(result, Err)


def test_audiogram_point_validation():
    good = AudiogramPoint(ear=Ear.LEFT, frequency_hz=1000, threshold_db=20)
    assert isinstance(validate_audiogram_point(good), Ok)
    bad = AudiogramPoint(ear=Ear.LEFT, frequency_hz=333, threshold_db=20)
    assert isinstance(validate_audiogram_point(bad), Err)


# ---------------------------------------------------------------------------
# Completeness
# ---------------------------------------------------------------------------


def test_audiogram_complete_diagnostic_requires_all_frequencies_both_ears():
    points = []
    for ear in (Ear.LEFT, Ear.RIGHT):
        for f in REQUIRED_DIAGNOSTIC_FREQUENCIES:
            points.append(AudiogramPoint(ear=ear, frequency_hz=f, threshold_db=20))
    ag = build_audiogram(points)
    assert isinstance(audiogram_complete(ag), Ok)


def test_audiogram_complete_screening_subset():
    points = []
    for ear in (Ear.LEFT, Ear.RIGHT):
        for f in REQUIRED_SCREENING_FREQUENCIES:
            points.append(AudiogramPoint(ear=ear, frequency_hz=f, threshold_db=20))
    ag = build_audiogram(points)
    assert isinstance(
        audiogram_complete(ag, REQUIRED_SCREENING_FREQUENCIES), Ok
    )


def test_audiogram_complete_reports_missing():
    points = [AudiogramPoint(Ear.LEFT, 1000, 20), AudiogramPoint(Ear.RIGHT, 1000, 20)]
    ag = build_audiogram(points)
    result = audiogram_complete(ag, REQUIRED_SCREENING_FREQUENCIES)
    assert isinstance(result, Err)
    assert any("500 Hz" in m for m in result.error)


# ---------------------------------------------------------------------------
# Algorithm conformance from real session
# ---------------------------------------------------------------------------


def test_step_sizes_correct_after_real_session():
    def oracle(stim):
        return stim.level_db >= 20

    state = run_session(Ear.LEFT, 1000, oracle, start_db=40).value
    assert step_sizes_correct(state.presentations) is True


def test_step_sizes_correct_detects_bad_sequence():
    # 30 -> 30 (no change) after a no-response is illegal.
    bad = (
        Presentation(db_level=30, responded=False, ascending=False),
        Presentation(db_level=30, responded=False, ascending=True),
    )
    assert step_sizes_correct(bad) is False


def test_state_is_iec_conformant_for_real_session():
    def oracle(stim):
        return stim.level_db >= 30

    state = run_session(Ear.LEFT, 1000, oracle, start_db=40).value
    assert isinstance(state_is_iec_conformant(state), Ok)

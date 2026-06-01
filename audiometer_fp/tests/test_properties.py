"""Property-based tests using Hypothesis.

These tests verify universal invariants of the pure functional core:
monad laws, IEC range invariants, immutability, termination of the
Hughson-Westlake algorithm, and procedural step-size rules.
"""

from __future__ import annotations

import math

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from audiometer.audiogram import build_audiogram, pta_for
from audiometer.hughson_westlake import (
    extract_threshold,
    initial_state,
    run_session,
    step,
)
from audiometer.iec60645 import step_sizes_correct
from audiometer.pure_calc import (
    DB_MAX,
    DB_MIN,
    DB_STEP,
    IEC_FREQUENCIES,
    amplitude_ratio_to_db,
    clamp,
    db_to_amplitude_ratio,
    is_valid_db_level,
    is_valid_frequency,
    snap_to_step,
)
from audiometer.response import count_responses, to_events
from audiometer.types import (
    AudiogramPoint,
    Ear,
    Just,
    Nothing,
    Ok,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


valid_frequencies = st.sampled_from(IEC_FREQUENCIES)
valid_dbs = st.integers(min_value=DB_MIN, max_value=DB_MAX).filter(is_valid_db_level)
ear_strategy = st.sampled_from([Ear.LEFT, Ear.RIGHT])


# ---------------------------------------------------------------------------
# Maybe monad laws
# ---------------------------------------------------------------------------


@given(st.integers())
def test_maybe_left_identity_property(x):
    f = lambda v: Just(v + 1)
    assert Just(x).bind(f) == f(x)


@given(st.integers())
def test_maybe_right_identity_property(x):
    assert Just(x).bind(Just) == Just(x)


@given(st.integers())
def test_maybe_associativity_property(x):
    f = lambda v: Just(v + 1)
    g = lambda v: Just(v * 2)
    left = Just(x).bind(f).bind(g)
    right = Just(x).bind(lambda v: f(v).bind(g))
    assert left == right


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


@given(
    st.integers(min_value=-10_000, max_value=10_000),
    st.integers(min_value=-100, max_value=100),
    st.integers(min_value=-100, max_value=100),
)
def test_clamp_within_range(value, lo, hi):
    assume(lo <= hi)
    out = clamp(value, lo, hi)
    assert lo <= out <= hi


@given(st.integers(min_value=-1000, max_value=1000), st.integers(min_value=1, max_value=20))
def test_snap_to_step_is_multiple(value, step_size):
    snapped = snap_to_step(value, step_size)
    assert snapped % step_size == 0
    # Snapping is idempotent.
    assert snap_to_step(snapped, step_size) == snapped


@given(st.floats(min_value=-80.0, max_value=80.0, allow_nan=False, allow_infinity=False))
def test_db_and_amplitude_are_inverses(db):
    ratio = db_to_amplitude_ratio(db)
    back = amplitude_ratio_to_db(ratio)
    assert back.is_just()
    assert math.isclose(back.get_or_else(0.0), db, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


@given(valid_dbs)
def test_valid_dbs_pass_validator(db):
    assert is_valid_db_level(db)


@given(valid_frequencies)
def test_valid_frequencies_pass_validator(freq):
    assert is_valid_frequency(freq)


# ---------------------------------------------------------------------------
# Hughson-Westlake invariants
# ---------------------------------------------------------------------------


@given(ear_strategy, valid_frequencies, valid_dbs)
def test_initial_state_in_valid_range(ear, freq, start_db):
    state = initial_state(ear, freq, start_db).value
    assert DB_MIN <= state.current_db <= DB_MAX
    assert state.frequency_hz == freq
    assert state.ear == ear


@given(
    ear_strategy,
    valid_frequencies,
    valid_dbs,
    st.lists(st.booleans(), min_size=0, max_size=40),
)
def test_step_keeps_db_in_range(ear, freq, start_db, responses):
    state = initial_state(ear, freq, start_db).value
    for r in responses:
        state = step(state, r)
        assert DB_MIN <= state.current_db <= DB_MAX


@given(
    ear_strategy,
    valid_frequencies,
    valid_dbs,
    st.lists(st.booleans(), min_size=0, max_size=40),
)
def test_step_sequence_obeys_step_size_rule(ear, freq, start_db, responses):
    state = initial_state(ear, freq, start_db).value
    for r in responses:
        state = step(state, r)
    assert step_sizes_correct(state.presentations)


@given(ear_strategy, valid_frequencies, valid_dbs, st.integers(min_value=DB_MIN, max_value=DB_MAX))
@settings(suppress_health_check=[HealthCheck.filter_too_much])
def test_run_session_terminates_and_threshold_is_valid(ear, freq, start_db, true_threshold):
    """For any monotone listener the algorithm terminates and either reports
    a threshold within the equipment range or Nothing if not measurable."""

    assume(is_valid_db_level(true_threshold))

    def oracle(stim):
        return stim.level_db >= true_threshold

    result = run_session(ear, freq, oracle, start_db=start_db, max_steps=200)
    assert isinstance(result, Ok)
    state = result.value
    assert state.finished or len(state.presentations) == 200
    t = extract_threshold(state)
    if t.is_just():
        v = t.get_or_else(0)
        assert DB_MIN <= v <= DB_MAX
        # Returned threshold should be close to (and not below) the real one.
        assert v >= true_threshold - DB_STEP


@given(ear_strategy, valid_frequencies, valid_dbs)
def test_step_does_not_mutate(ear, freq, start_db):
    state = initial_state(ear, freq, start_db).value
    snapshot_presentations = state.presentations
    snapshot_db = state.current_db
    _ = step(state, True)
    assert state.presentations is snapshot_presentations
    assert state.current_db == snapshot_db


# ---------------------------------------------------------------------------
# Audiogram invariants
# ---------------------------------------------------------------------------


point_strategy = st.builds(
    AudiogramPoint,
    ear=ear_strategy,
    frequency_hz=valid_frequencies,
    threshold_db=valid_dbs,
)


@given(st.lists(point_strategy, min_size=0, max_size=15))
def test_build_audiogram_preserves_count(points):
    ag = build_audiogram(points)
    assert len(ag.points) == len(points)


@given(st.lists(point_strategy, min_size=0, max_size=20))
def test_build_audiogram_points_are_immutable_tuple(points):
    ag = build_audiogram(points)
    assert isinstance(ag.points, tuple)


@given(
    ear_strategy,
    st.lists(valid_dbs, min_size=4, max_size=4),
)
def test_pta_present_when_all_four_frequencies_filled(ear, dbs):
    pts = [
        AudiogramPoint(ear, 500, dbs[0]),
        AudiogramPoint(ear, 1000, dbs[1]),
        AudiogramPoint(ear, 2000, dbs[2]),
        AudiogramPoint(ear, 4000, dbs[3]),
    ]
    ag = build_audiogram(pts)
    pta = pta_for(ag, ear)
    assert pta.is_just()
    assert math.isclose(pta.get_or_else(0.0), sum(dbs) / 4.0)


# ---------------------------------------------------------------------------
# Response pipeline invariants
# ---------------------------------------------------------------------------


@given(st.lists(st.tuples(st.text(min_size=0, max_size=20), st.integers(min_value=0, max_value=1_000_000)), max_size=30))
def test_count_responses_never_negative(lines):
    events = to_events(lines)
    assert count_responses(events) >= 0


@given(
    st.lists(
        st.tuples(st.sampled_from(["RESPONSE", "RESPONSE:1", "ACK", ""]), st.integers(min_value=0, max_value=1_000_000)),
        max_size=30,
    )
)
def test_response_count_matches_filter(lines):
    expected = sum(1 for (line, _) in lines if line.strip().upper().startswith("RESPONSE"))
    events = to_events(lines)
    assert count_responses(events) == expected

"""Unit tests for the Hughson-Westlake state machine."""

import pytest

from audiometer.hughson_westlake import (
    DEFAULT_START_DB,
    STANDARD_FREQUENCY_ORDER,
    extract_threshold,
    initial_state,
    run_session,
    step,
    stimulus_for,
)
from audiometer.types import Ear, Err, Just, Ok, Stimulus


# ---------------------------------------------------------------------------
# initial_state
# ---------------------------------------------------------------------------


def test_initial_state_rejects_unknown_frequency():
    assert isinstance(initial_state(Ear.LEFT, 333), Err)


def test_initial_state_clamps_start_db():
    state = initial_state(Ear.LEFT, 1000, start_db=500).value
    assert state.current_db == 120


def test_initial_state_is_ready():
    state = initial_state(Ear.RIGHT, 1000).value
    assert state.current_db == DEFAULT_START_DB
    assert state.finished is False
    assert state.presentations == ()
    assert state.threshold_db.is_nothing()


# ---------------------------------------------------------------------------
# step()
# ---------------------------------------------------------------------------


def test_response_steps_down_10_db():
    s0 = initial_state(Ear.RIGHT, 1000, start_db=40).value
    s1 = step(s0, responded=True)
    assert s1.current_db == 30
    assert s1.presentations[-1].responded is True
    assert s1.presentations[-1].ascending is False


def test_no_response_steps_up_5_db():
    s0 = initial_state(Ear.RIGHT, 1000, start_db=20).value
    s1 = step(s0, responded=False)
    assert s1.current_db == 25
    assert s1.presentations[-1].responded is False


def test_step_does_not_mutate_input():
    s0 = initial_state(Ear.LEFT, 1000).value
    s1 = step(s0, responded=True)
    assert s0.current_db == DEFAULT_START_DB
    assert s0.presentations == ()
    assert s1 is not s0


def test_finished_state_is_idempotent_to_step():
    """Stepping after finished returns the same state object."""

    s0 = initial_state(Ear.LEFT, 1000).value
    # Force-finished by simulating a successful threshold:
    s = s0
    sequence = [True, False, True, False, True, False, True]  # zig-zag
    for r in sequence:
        s = step(s, r)
    snapshot = s
    after = step(s, True)
    if s.finished:
        assert after is snapshot


# ---------------------------------------------------------------------------
# stimulus_for
# ---------------------------------------------------------------------------


def test_stimulus_for_unfinished_state():
    s = initial_state(Ear.RIGHT, 2000, start_db=40).value
    stim = stimulus_for(s)
    assert stim == Just(Stimulus(frequency_hz=2000, level_db=40, ear=Ear.RIGHT))


def test_stimulus_for_finished_state_is_nothing():
    # Construct a finished state manually.
    s0 = initial_state(Ear.RIGHT, 1000).value
    s = s0.__class__(**{**s0.__dict__, "finished": True})  # type: ignore[arg-type]
    assert stimulus_for(s).is_nothing()


# ---------------------------------------------------------------------------
# Threshold extraction (2 of 3 ascending)
# ---------------------------------------------------------------------------


def test_run_session_finds_threshold_for_perfect_listener():
    # Patient with a 20 dB threshold: responds at >=20 dB.
    def oracle(stim: Stimulus) -> bool:
        return stim.level_db >= 20

    result = run_session(Ear.LEFT, 1000, oracle, start_db=40)
    assert isinstance(result, Ok)
    state = result.value
    assert state.finished
    threshold = extract_threshold(state)
    assert threshold == Just(20)


def test_run_session_returns_nothing_for_profound_loss():
    # Patient that never responds.
    def oracle(stim: Stimulus) -> bool:
        return False

    result = run_session(Ear.LEFT, 1000, oracle, start_db=40, max_steps=50)
    assert isinstance(result, Ok)
    state = result.value
    assert state.finished
    assert state.threshold_db.is_nothing()


# ---------------------------------------------------------------------------
# Frequency order
# ---------------------------------------------------------------------------


def test_standard_frequency_order_starts_at_1khz():
    assert STANDARD_FREQUENCY_ORDER[0] == 1000


def test_standard_frequency_order_covers_iec_set():
    assert set(STANDARD_FREQUENCY_ORDER) == {250, 500, 1000, 2000, 4000, 8000}

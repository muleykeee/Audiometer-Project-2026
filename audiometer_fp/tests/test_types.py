"""Unit tests for the immutable types and the Maybe / Result monads."""

import pytest

from audiometer.types import (
    Audiogram,
    AudiogramPoint,
    Ear,
    Err,
    HWState,
    Just,
    Nothing,
    Ok,
    Presentation,
    Stimulus,
    from_optional,
)


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


def test_stimulus_is_frozen():
    s = Stimulus(frequency_hz=1000, level_db=40, ear=Ear.LEFT)
    with pytest.raises(Exception):
        s.level_db = 50  # type: ignore[misc]


def test_audiogram_with_point_returns_new_value():
    base = Audiogram()
    point = AudiogramPoint(ear=Ear.LEFT, frequency_hz=1000, threshold_db=20)
    updated = base.with_point(point)
    assert base.points == ()
    assert updated.points == (point,)
    assert base is not updated


def test_hwstate_uses_tuple_for_history():
    state = HWState(ear=Ear.RIGHT, frequency_hz=1000, current_db=30)
    assert isinstance(state.presentations, tuple)


# ---------------------------------------------------------------------------
# Maybe monad laws
# ---------------------------------------------------------------------------


def test_just_map_applies_function():
    assert Just(2).map(lambda x: x * 3) == Just(6)


def test_nothing_map_short_circuits():
    assert Nothing().map(lambda x: x + 1) == Nothing()


def test_just_bind_chains_computation():
    assert Just(10).bind(lambda x: Just(x - 1)).bind(lambda x: Just(x * 2)) == Just(18)


def test_nothing_bind_short_circuits():
    assert Nothing().bind(lambda x: Just(x)) == Nothing()


def test_get_or_else_uses_default_on_nothing():
    assert Nothing().get_or_else(42) == 42
    assert Just(7).get_or_else(42) == 7


def test_maybe_filter():
    assert Just(5).filter(lambda x: x > 0) == Just(5)
    assert Just(-1).filter(lambda x: x > 0) == Nothing()
    assert Nothing().filter(lambda x: True) == Nothing()


def test_from_optional():
    assert from_optional(None) == Nothing()
    assert from_optional(3) == Just(3)


# Monad left identity:   bind(unit a, f) == f a
def test_maybe_left_identity():
    f = lambda x: Just(x + 1)
    assert Just(5).bind(f) == f(5)


# Monad right identity:  bind(m, unit) == m
def test_maybe_right_identity():
    m = Just(5)
    assert m.bind(Just) == m
    assert Nothing().bind(Just) == Nothing()


# Monad associativity:   bind(bind(m, f), g) == bind(m, lambda x: bind(f x, g))
def test_maybe_associativity():
    m = Just(3)
    f = lambda x: Just(x * 2)
    g = lambda x: Just(x - 1)
    left = m.bind(f).bind(g)
    right = m.bind(lambda x: f(x).bind(g))
    assert left == right


# ---------------------------------------------------------------------------
# Result monad laws
# ---------------------------------------------------------------------------


def test_ok_map_and_bind():
    assert Ok(2).map(lambda x: x + 1) == Ok(3)
    assert Ok(2).bind(lambda x: Ok(x * 2)) == Ok(4)


def test_err_short_circuits_map_and_bind():
    e = Err("oops")
    assert e.map(lambda x: x + 1) == e
    assert e.bind(lambda x: Ok(x)) == e


def test_err_map_err_transforms_error():
    assert Err("oops").map_err(str.upper) == Err("OOPS")


def test_result_to_maybe():
    assert Ok(5).to_maybe() == Just(5)
    assert Err("x").to_maybe() == Nothing()


# ---------------------------------------------------------------------------
# Presentation immutability
# ---------------------------------------------------------------------------


def test_presentation_is_frozen():
    p = Presentation(db_level=30, responded=True, ascending=False)
    with pytest.raises(Exception):
        p.db_level = 0  # type: ignore[misc]

"""Pure functional implementation of the Hughson-Westlake threshold search.

The procedure documented by the Biomedical team and codified in IEC 60645-1
(modified Hughson-Westlake, "10 dB down on response, 5 dB up on no
response", threshold = lowest level with at least 2 ascending responses
out of 3 trials) is implemented here as a state machine over the immutable
:class:`HWState`.

No function in this module mutates input; every state transition returns a
*new* :class:`HWState`.
"""

from __future__ import annotations

from dataclasses import replace
from functools import reduce
from typing import Tuple

from audiometer.pure_calc import (
    DB_MAX,
    DB_MIN,
    DB_STEP,
    IEC_FREQUENCIES,
    clamp,
    is_valid_db_level,
    is_valid_frequency,
)
from audiometer.types import (
    Ear,
    Err,
    HWState,
    Just,
    Maybe,
    Nothing,
    Ok,
    Presentation,
    Result,
    Stimulus,
)

# Standard test order: 1 kHz first (most reliable), then ascending high
# frequencies, then a 1 kHz retest is optional, then low frequencies.
STANDARD_FREQUENCY_ORDER: Tuple[int, ...] = (1000, 2000, 4000, 8000, 500, 250)

# Familiarisation start level (dB HL) recommended by ASHA / IEC 60645-1.
DEFAULT_START_DB: int = 30

# Threshold criterion: minimum positive ascending responses required, and
# the total ascending trials at the same level needed to make a decision.
MIN_POSITIVE_RESPONSES: int = 2
MIN_TOTAL_ASCENDING_TRIALS: int = 3

# Step sizes mandated by the procedure.
STEP_DOWN_DB: int = -10
STEP_UP_DB: int = 5


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def initial_state(ear: Ear, frequency_hz: int, start_db: int = DEFAULT_START_DB) -> Result[HWState, str]:
    """Create the starting state for one frequency / ear pair.

    Returns :class:`Err` if any IEC 60645-1 constraint is violated.
    """

    if not is_valid_frequency(frequency_hz):
        return Err(f"frequency {frequency_hz} Hz not in IEC 60645-1 set {IEC_FREQUENCIES}")
    snapped = clamp(start_db, DB_MIN, DB_MAX)
    if not is_valid_db_level(snapped):
        return Err(f"start dB {start_db} is not aligned to {DB_STEP} dB step")
    return Ok(
        HWState(
            ear=ear,
            frequency_hz=frequency_hz,
            current_db=snapped,
        )
    )


# ---------------------------------------------------------------------------
# State transition
# ---------------------------------------------------------------------------


def _next_db(current_db: int, responded: bool) -> int:
    """Pure stepping rule: -10 on response, +5 on no response, clamped."""

    delta = STEP_DOWN_DB if responded else STEP_UP_DB
    return clamp(current_db + delta, DB_MIN, DB_MAX)


def _is_ascending_presentation(previous: Tuple[Presentation, ...]) -> bool:
    """A presentation is *ascending* when it follows a no-response trial."""

    if len(previous) == 0:
        return False
    return not previous[-1].responded


def step(state: HWState, responded: bool) -> HWState:
    """Apply one response to ``state`` and return the resulting state.

    The function is total: calling it on a finished state is a no-op that
    simply returns the same state value.
    """

    if state.finished:
        return state

    presentation = Presentation(
        db_level=state.current_db,
        responded=responded,
        ascending=_is_ascending_presentation(state.presentations),
    )
    new_presentations = state.presentations + (presentation,)

    threshold = _try_extract_threshold(new_presentations)
    if threshold.is_just():
        return replace(
            state,
            presentations=new_presentations,
            threshold_db=threshold,
            finished=True,
        )

    next_db = _next_db(state.current_db, responded)
    # If we have hit the equipment ceiling without ever getting a response,
    # the threshold cannot be measured at this frequency. Mark finished.
    if next_db == state.current_db and not responded and state.current_db >= DB_MAX:
        return replace(
            state,
            presentations=new_presentations,
            threshold_db=Nothing(),
            finished=True,
        )

    return replace(
        state,
        current_db=next_db,
        presentations=new_presentations,
    )


# ---------------------------------------------------------------------------
# Threshold extraction (pure, map/filter/reduce)
# ---------------------------------------------------------------------------


def _try_extract_threshold(presentations: Tuple[Presentation, ...]) -> Maybe[int]:
    """Apply the 2-of-3 ascending rule to the full presentation history.

    Implementation uses map/filter/reduce over the immutable history.
    """

    ascending = tuple(filter(lambda p: p.ascending, presentations))
    if len(ascending) == 0:
        return Nothing()

    # Bucket ascending presentations by dB level using reduce.
    def add_to_buckets(acc: dict, p: Presentation) -> dict:
        bucket = acc.get(p.db_level, (0, 0))
        positives, total = bucket
        return {**acc, p.db_level: (positives + (1 if p.responded else 0), total + 1)}

    buckets = reduce(add_to_buckets, ascending, {})

    qualifying = list(
        map(
            lambda kv: kv[0],
            filter(
                lambda kv: kv[1][1] >= MIN_TOTAL_ASCENDING_TRIALS
                and kv[1][0] >= MIN_POSITIVE_RESPONSES,
                buckets.items(),
            ),
        )
    )
    if not qualifying:
        return Nothing()
    return Just(min(qualifying))


def extract_threshold(state: HWState) -> Maybe[int]:
    """Public accessor: same logic, exposed on a state value."""

    return _try_extract_threshold(state.presentations)


# ---------------------------------------------------------------------------
# Driving the test
# ---------------------------------------------------------------------------


def stimulus_for(state: HWState) -> Maybe[Stimulus]:
    """Return the next stimulus to play, or :class:`Nothing` if done."""

    if state.finished:
        return Nothing()
    return Just(
        Stimulus(
            frequency_hz=state.frequency_hz,
            level_db=state.current_db,
            ear=state.ear,
        )
    )


def run_session(
    ear: Ear,
    frequency_hz: int,
    responses_fn,
    start_db: int = DEFAULT_START_DB,
    max_steps: int = 100,
) -> Result[HWState, str]:
    """Drive a full Hughson-Westlake session at one frequency.

    ``responses_fn(stimulus) -> bool`` is supplied by the caller; this keeps
    all side effects (serial I/O, virtual patient model) out of the algorithm.
    The function is otherwise pure: the same ``responses_fn`` produces the
    same final state.
    """

    initial = initial_state(ear, frequency_hz, start_db)
    if isinstance(initial, Err):
        return initial

    def take_one_step(state: HWState, _: int) -> HWState:
        if state.finished:
            return state
        stim = stimulus_for(state)
        if stim.is_nothing():
            return state
        responded = bool(responses_fn(stim.get_or_else(None)))
        return step(state, responded)

    final = reduce(take_one_step, range(max_steps), initial.value)
    return Ok(final)

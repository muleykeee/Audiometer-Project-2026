"""IEC 60645-1 conformance rules expressed as pure validators.

The Biomedical team hands us the textual specification; this module turns
each rule into a function we can exercise from unit and property tests.

Each validator either returns :class:`Ok` with the validated value or
:class:`Err` with a human-readable list of violations. No exceptions are
raised for domain errors, in line with the YMH 334 brief that asks for
side-effect-free error handling via the Maybe / Result pattern.
"""

from __future__ import annotations

from typing import Tuple

from audiometer.pure_calc import (
    DB_MAX,
    DB_MIN,
    DB_STEP,
    IEC_FREQUENCIES,
    is_valid_db_level,
    is_valid_frequency,
)
from audiometer.types import (
    Audiogram,
    AudiogramPoint,
    Ear,
    Err,
    HWState,
    Ok,
    Presentation,
    Result,
    Stimulus,
)

# Frequencies that a Type-4 screening audiometer (the closest type to a
# Proteus-simulated device) is required to support.
REQUIRED_SCREENING_FREQUENCIES: Tuple[int, ...] = (500, 1000, 2000, 4000)

# Frequencies a Type-1 diagnostic audiometer must support.
REQUIRED_DIAGNOSTIC_FREQUENCIES: Tuple[int, ...] = IEC_FREQUENCIES


# ---------------------------------------------------------------------------
# Stimulus / point validators
# ---------------------------------------------------------------------------


def validate_stimulus(stim: Stimulus) -> Result[Stimulus, Tuple[str, ...]]:
    """Validate a single stimulus against IEC 60645-1 ranges and steps."""

    errors = []
    if not is_valid_frequency(stim.frequency_hz):
        errors.append(
            f"frequency {stim.frequency_hz} Hz outside IEC set {IEC_FREQUENCIES}"
        )
    if not is_valid_db_level(stim.level_db):
        errors.append(
            f"level {stim.level_db} dB outside [{DB_MIN}, {DB_MAX}] or not a {DB_STEP} dB step"
        )
    if errors:
        return Err(tuple(errors))
    return Ok(stim)


def validate_audiogram_point(point: AudiogramPoint) -> Result[AudiogramPoint, Tuple[str, ...]]:
    """Validate a single audiogram point."""

    errors = []
    if not is_valid_frequency(point.frequency_hz):
        errors.append(f"frequency {point.frequency_hz} Hz outside IEC set")
    if not is_valid_db_level(point.threshold_db):
        errors.append(f"threshold {point.threshold_db} dB outside IEC range / step")
    if errors:
        return Err(tuple(errors))
    return Ok(point)


# ---------------------------------------------------------------------------
# Audiogram-level validation
# ---------------------------------------------------------------------------


def audiogram_complete(
    audiogram: Audiogram,
    required_frequencies: Tuple[int, ...] = REQUIRED_DIAGNOSTIC_FREQUENCIES,
) -> Result[Audiogram, Tuple[str, ...]]:
    """An audiogram is complete when every required frequency is measured
    in *both* ears."""

    missing: list[str] = []
    for ear in (Ear.LEFT, Ear.RIGHT):
        present = {p.frequency_hz for p in audiogram.points if p.ear == ear}
        for freq in required_frequencies:
            if freq not in present:
                missing.append(f"{ear.value} {freq} Hz missing")
    if missing:
        return Err(tuple(missing))
    return Ok(audiogram)


# ---------------------------------------------------------------------------
# Algorithm-level conformance
# ---------------------------------------------------------------------------


def step_sizes_correct(presentations: Tuple[Presentation, ...]) -> bool:
    """The procedural rule ("10 dB down, 5 dB up") must hold for every
    consecutive pair of presentations. At the equipment floor / ceiling the
    step is clamped, so the expected next level is the *clamped* value of
    the nominal step.
    """

    for prev, nxt in zip(presentations, presentations[1:]):
        if prev.responded:
            expected = max(DB_MIN, prev.db_level - 10)
        else:
            expected = min(DB_MAX, prev.db_level + 5)
        if nxt.db_level != expected:
            return False
    return True


def state_is_iec_conformant(state: HWState) -> Result[HWState, Tuple[str, ...]]:
    """Combined IEC 60645-1 sanity check for a finished H-W state."""

    errors: list[str] = []
    if not is_valid_frequency(state.frequency_hz):
        errors.append(f"frequency {state.frequency_hz} Hz outside IEC set")
    for pres in state.presentations:
        if not is_valid_db_level(pres.db_level):
            errors.append(
                f"presentation at {pres.db_level} dB violates range / step"
            )
    if not step_sizes_correct(state.presentations):
        errors.append("step sizes deviate from the 10-down / 5-up rule")
    if errors:
        return Err(tuple(errors))
    return Ok(state)

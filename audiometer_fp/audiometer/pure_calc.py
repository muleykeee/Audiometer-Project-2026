"""Pure mathematical and audiology helper functions.

Every function in this module is referentially transparent: given the same
inputs it always produces the same output and performs no I/O. This is the
property the YMH 334 brief asks us to maintain for "all medical
calculations".
"""

from __future__ import annotations

import math
from typing import Tuple

from audiometer.types import Just, Maybe, Nothing


# IEC 60645-1 compliant frequency set (Hz)
IEC_FREQUENCIES: Tuple[int, ...] = (250, 500, 1000, 2000, 4000, 8000)

# Standard clinical audiometer dB HL range
DB_MIN: int = -10
DB_MAX: int = 120
DB_STEP: int = 5

# Reference Equivalent Threshold Sound Pressure Levels (RETSPL) for
# supra-aural earphones, per ISO 389-1 / IEC 60645-1 Annex.
RETSPL_DB_SPL = {
    250: 25.5,
    500: 11.5,
    1000: 7.0,
    2000: 9.0,
    4000: 9.5,
    8000: 13.0,
}


# ---------------------------------------------------------------------------
# Numeric helpers (pure)
# ---------------------------------------------------------------------------


def clamp(value: int, low: int, high: int) -> int:
    """Clamp ``value`` to the closed interval ``[low, high]``."""

    if value < low:
        return low
    if value > high:
        return high
    return value


def snap_to_step(value: int, step: int = DB_STEP) -> int:
    """Snap ``value`` to the nearest multiple of ``step`` (banker-free)."""

    if step <= 0:
        raise ValueError("step must be positive")
    return int(round(value / step)) * step


# ---------------------------------------------------------------------------
# Validation predicates (pure)
# ---------------------------------------------------------------------------


def is_valid_frequency(freq_hz: int) -> bool:
    return freq_hz in IEC_FREQUENCIES


def is_valid_db_level(db: int) -> bool:
    return DB_MIN <= db <= DB_MAX and (db - DB_MIN) % DB_STEP == 0


# ---------------------------------------------------------------------------
# dB conversions (pure)
# ---------------------------------------------------------------------------


def db_to_amplitude_ratio(db: float) -> float:
    """Convert a dB value to a linear amplitude ratio (20 dB rule)."""

    return 10.0 ** (db / 20.0)


def amplitude_ratio_to_db(ratio: float) -> Maybe[float]:
    """Inverse of :func:`db_to_amplitude_ratio` guarded by Maybe."""

    if ratio <= 0.0:
        return Nothing()
    return Just(20.0 * math.log10(ratio))


def hl_to_spl(db_hl: float, frequency_hz: int) -> Maybe[float]:
    """Convert dB HL to dB SPL for the given frequency.

    Returns :class:`Nothing` if the frequency is not in the IEC reference
    table.
    """

    reference = RETSPL_DB_SPL.get(frequency_hz)
    if reference is None:
        return Nothing()
    return Just(db_hl + reference)


# ---------------------------------------------------------------------------
# DAC / DDS helpers (pure)
# ---------------------------------------------------------------------------


def dac_code(amplitude_normalized: float, bits: int = 12) -> int:
    """Map a ``[-1.0, 1.0]`` amplitude to an unsigned DAC code (MCP4921 = 12-bit).

    The amplitude is centred at mid-scale so the resulting code is suitable
    for driving the LM358 buffer directly.
    """

    if bits <= 0:
        raise ValueError("bits must be positive")
    full_scale = (1 << bits) - 1
    mid = full_scale // 2
    clipped = max(-1.0, min(1.0, amplitude_normalized))
    return int(round(mid + clipped * mid))


def sine_sample(t_seconds: float, frequency_hz: float, amplitude: float = 1.0) -> float:
    """Return one sample of a continuous sinusoid (no quantisation)."""

    return amplitude * math.sin(2.0 * math.pi * frequency_hz * t_seconds)


def dds_phase_increment(frequency_hz: float, sample_rate_hz: float, phase_bits: int = 32) -> int:
    """Compute the phase increment for a direct-digital-synthesis loop."""

    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    return int(round((frequency_hz / sample_rate_hz) * (1 << phase_bits)))


# ---------------------------------------------------------------------------
# Pure-tone average and hearing-loss classification
# ---------------------------------------------------------------------------


def pure_tone_average(thresholds: Tuple[int, ...]) -> Maybe[float]:
    """Compute the arithmetic mean of a tuple of thresholds."""

    if len(thresholds) == 0:
        return Nothing()
    return Just(sum(thresholds) / len(thresholds))


def classify_hearing_loss(pta_db: float) -> str:
    """Classify hearing loss following the WHO / ASHA grading scheme."""

    if pta_db < 26:
        return "Normal"
    if pta_db < 41:
        return "Mild"
    if pta_db < 56:
        return "Moderate"
    if pta_db < 71:
        return "Moderately Severe"
    if pta_db < 91:
        return "Severe"
    return "Profound"

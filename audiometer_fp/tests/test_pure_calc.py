"""Unit tests for pure numeric helpers."""

import math

import pytest

from audiometer.pure_calc import (
    DB_MAX,
    DB_MIN,
    DB_STEP,
    IEC_FREQUENCIES,
    RETSPL_DB_SPL,
    amplitude_ratio_to_db,
    classify_hearing_loss,
    clamp,
    dac_code,
    db_to_amplitude_ratio,
    dds_phase_increment,
    hl_to_spl,
    is_valid_db_level,
    is_valid_frequency,
    pure_tone_average,
    sine_sample,
    snap_to_step,
)
from audiometer.types import Just, Nothing


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def test_valid_iec_frequencies_pass():
    for f in IEC_FREQUENCIES:
        assert is_valid_frequency(f) is True


@pytest.mark.parametrize("bad", [0, 100, 300, 750, 1500, 9000])
def test_non_iec_frequencies_fail(bad):
    assert is_valid_frequency(bad) is False


def test_db_level_step_and_bounds():
    for db in range(DB_MIN, DB_MAX + 1, DB_STEP):
        assert is_valid_db_level(db) is True
    assert is_valid_db_level(DB_MIN - 1) is False
    assert is_valid_db_level(DB_MAX + 1) is False
    assert is_valid_db_level(7) is False  # not on 5 dB grid


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10


def test_snap_to_step():
    assert snap_to_step(11, 5) == 10
    assert snap_to_step(12, 5) == 10
    assert snap_to_step(13, 5) == 15
    with pytest.raises(ValueError):
        snap_to_step(10, 0)


# ---------------------------------------------------------------------------
# dB <-> amplitude
# ---------------------------------------------------------------------------


def test_db_to_amplitude_is_inverse_of_amplitude_to_db():
    for db in (0.0, 6.0, 20.0, -10.0, 40.0):
        ratio = db_to_amplitude_ratio(db)
        back = amplitude_ratio_to_db(ratio)
        assert back.is_just()
        assert math.isclose(back.get_or_else(0.0), db, abs_tol=1e-9)


def test_amplitude_to_db_rejects_non_positive():
    assert amplitude_ratio_to_db(0.0) == Nothing()
    assert amplitude_ratio_to_db(-1.0) == Nothing()


def test_hl_to_spl_uses_reference_table():
    for freq, ref in RETSPL_DB_SPL.items():
        spl = hl_to_spl(40.0, freq)
        assert spl.is_just()
        assert math.isclose(spl.get_or_else(0.0), 40.0 + ref)
    # Unknown frequency -> Nothing
    assert hl_to_spl(40.0, 333) == Nothing()


# ---------------------------------------------------------------------------
# DAC and DDS
# ---------------------------------------------------------------------------


def test_dac_code_midpoint_is_half_scale():
    assert dac_code(0.0, bits=12) == 2047


def test_dac_code_clips_to_range():
    assert dac_code(2.0, bits=12) == 4094
    assert dac_code(-2.0, bits=12) == 0


def test_dac_code_zero_for_negative_full_scale():
    assert dac_code(-1.0, bits=12) == 0


def test_dac_code_requires_positive_bits():
    with pytest.raises(ValueError):
        dac_code(0.0, bits=0)


def test_sine_sample_period():
    f = 1000.0
    a = sine_sample(0.0, f)
    b = sine_sample(1.0 / f, f)
    assert math.isclose(a, b, abs_tol=1e-9)


def test_dds_phase_increment_positive():
    assert dds_phase_increment(1000.0, 48000.0, 32) > 0
    with pytest.raises(ValueError):
        dds_phase_increment(1000.0, 0.0)


# ---------------------------------------------------------------------------
# Pure-tone average and classification
# ---------------------------------------------------------------------------


def test_pta_returns_mean_when_input_present():
    pta = pure_tone_average((10, 20, 30, 40))
    assert pta == Just(25.0)


def test_pta_returns_nothing_on_empty():
    assert pure_tone_average(()) == Nothing()


def test_classification_buckets():
    assert classify_hearing_loss(20) == "Normal"
    assert classify_hearing_loss(30) == "Mild"
    assert classify_hearing_loss(50) == "Moderate"
    assert classify_hearing_loss(65) == "Moderately Severe"
    assert classify_hearing_loss(80) == "Severe"
    assert classify_hearing_loss(95) == "Profound"

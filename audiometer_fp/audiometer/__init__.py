"""Audiometer functional-programming core (YMH 334).

All medical calculations are exposed as pure functions. Data is moved
through the system as immutable values. Side effects are isolated into
the :mod:`audiometer.serial_bridge` and :mod:`audiometer.cli` modules.
"""

from audiometer.types import (
    Maybe,
    Just,
    Nothing,
    Result,
    Ok,
    Err,
    Ear,
    ResponseEvent,
    Stimulus,
    Presentation,
    AudiogramPoint,
    Audiogram,
    HWState,
)

__all__ = [
    "Maybe",
    "Just",
    "Nothing",
    "Result",
    "Ok",
    "Err",
    "Ear",
    "ResponseEvent",
    "Stimulus",
    "Presentation",
    "AudiogramPoint",
    "Audiogram",
    "HWState",
]

__version__ = "1.0.0"

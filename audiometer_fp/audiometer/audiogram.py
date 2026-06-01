"""Pure functions for building and summarising an audiogram.

Audiogram values are immutable; every "modification" returns a fresh value.
All helpers are side-effect free except :func:`to_json_string`, which only
serialises an in-memory value to text.
"""

from __future__ import annotations

import json
from functools import reduce
from typing import Dict, Iterable, Tuple

from audiometer.pure_calc import (
    classify_hearing_loss,
    pure_tone_average,
)
from audiometer.types import (
    Audiogram,
    AudiogramPoint,
    Ear,
    Just,
    Maybe,
    Nothing,
)

# Frequencies considered in the standard 4-frequency PTA.
PTA_FREQUENCIES: Tuple[int, ...] = (500, 1000, 2000, 4000)


def build_audiogram(points: Iterable[AudiogramPoint]) -> Audiogram:
    """Fold an iterable of points into an immutable :class:`Audiogram`."""

    return reduce(lambda ag, p: ag.with_point(p), points, Audiogram())


def thresholds_for(audiogram: Audiogram, ear: Ear) -> Dict[int, int]:
    """Map frequency → threshold for one ear (latest value wins)."""

    relevant = filter(lambda p: p.ear == ear, audiogram.points)
    return reduce(lambda acc, p: {**acc, p.frequency_hz: p.threshold_db}, relevant, {})


def pta_for(audiogram: Audiogram, ear: Ear) -> Maybe[float]:
    """Compute the 4-frequency PTA for ``ear`` if all PTA frequencies exist."""

    thresholds_map = thresholds_for(audiogram, ear)
    selected = tuple(
        map(lambda f: thresholds_map[f], filter(lambda f: f in thresholds_map, PTA_FREQUENCIES))
    )
    if len(selected) != len(PTA_FREQUENCIES):
        return Nothing()
    return pure_tone_average(selected)


def classification_for(audiogram: Audiogram, ear: Ear) -> Maybe[str]:
    """Return the WHO classification label for ``ear`` if PTA available."""

    return pta_for(audiogram, ear).map(classify_hearing_loss)


def ears_match(audiogram: Audiogram, tolerance_db: int = 10) -> Maybe[bool]:
    """Both ears must have a PTA to be compared; result is Maybe[bool]."""

    left = pta_for(audiogram, Ear.LEFT)
    right = pta_for(audiogram, Ear.RIGHT)
    if left.is_nothing() or right.is_nothing():
        return Nothing()
    return Just(abs(left.get_or_else(0.0) - right.get_or_else(0.0)) <= tolerance_db)


def to_dict(audiogram: Audiogram) -> dict:
    """Serialise an audiogram to a plain Python dict (still pure)."""

    return {
        "points": [
            {
                "ear": p.ear.value,
                "frequency_hz": p.frequency_hz,
                "threshold_db": p.threshold_db,
            }
            for p in audiogram.points
        ]
    }


def to_json_string(audiogram: Audiogram, indent: int = 2) -> str:
    return json.dumps(to_dict(audiogram), indent=indent, sort_keys=True)

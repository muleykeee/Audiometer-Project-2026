"""Immutable data types and algebraic Maybe/Result for the audiometer FP core.

Every type in this module is immutable (``frozen=True`` dataclasses) so that
state transitions return *new* values instead of mutating shared state. This
is the foundation that allows the rest of the codebase to be written as pure
functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Callable, Generic, Tuple, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
F = TypeVar("F")


# ---------------------------------------------------------------------------
# Maybe monad (Optional pattern, side-effect free)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Just(Generic[T]):
    """A value is present."""

    value: T

    def is_just(self) -> bool:
        return True

    def is_nothing(self) -> bool:
        return False

    def map(self, f: Callable[[T], U]) -> "Maybe[U]":
        return Just(f(self.value))

    def bind(self, f: Callable[[T], "Maybe[U]"]) -> "Maybe[U]":
        return f(self.value)

    def get_or_else(self, default: T) -> T:
        return self.value

    def filter(self, predicate: Callable[[T], bool]) -> "Maybe[T]":
        return self if predicate(self.value) else Nothing()


@dataclass(frozen=True)
class Nothing:
    """No value is present (the Maybe equivalent of ``None``)."""

    def is_just(self) -> bool:
        return False

    def is_nothing(self) -> bool:
        return True

    def map(self, f: Callable[[T], U]) -> "Maybe[U]":
        return self  # type: ignore[return-value]

    def bind(self, f: Callable[[T], "Maybe[U]"]) -> "Maybe[U]":
        return self  # type: ignore[return-value]

    def get_or_else(self, default: T) -> T:
        return default

    def filter(self, predicate: Callable[[T], bool]) -> "Maybe[T]":
        return self  # type: ignore[return-value]


Maybe = Union[Just[T], Nothing]


def from_optional(value: "T | None") -> Maybe[T]:
    """Lift a Python ``Optional[T]`` value into the Maybe monad."""

    return Nothing() if value is None else Just(value)


# ---------------------------------------------------------------------------
# Result monad (success/error without exceptions)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def map(self, f: Callable[[T], U]) -> "Result[U, E]":
        return Ok(f(self.value))

    def map_err(self, f: Callable[[E], F]) -> "Result[T, F]":
        return self  # type: ignore[return-value]

    def bind(self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return f(self.value)

    def get_or_else(self, default: T) -> T:
        return self.value

    def to_maybe(self) -> Maybe[T]:
        return Just(self.value)


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def map(self, f: Callable[[T], U]) -> "Result[U, E]":
        return self  # type: ignore[return-value]

    def map_err(self, f: Callable[[E], F]) -> "Result[T, F]":
        return Err(f(self.error))

    def bind(self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return self  # type: ignore[return-value]

    def get_or_else(self, default: T) -> T:
        return default

    def to_maybe(self) -> Maybe[T]:
        return Nothing()


Result = Union[Ok[T], Err[E]]


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class Ear(str, Enum):
    """Which ear is currently under test."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"


@dataclass(frozen=True)
class Stimulus:
    """An immutable command sent toward the hardware DAC.

    A new ``Stimulus`` value is created for every presentation; existing
    values are never mutated.
    """

    frequency_hz: int
    level_db: int
    ear: Ear


@dataclass(frozen=True)
class ResponseEvent:
    """A raw response notification captured from the patient's button.

    Side-effecting code (the serial bridge) builds these values and hands
    them to the pure pipeline.
    """

    timestamp_ms: int
    raw_message: str


@dataclass(frozen=True)
class AudiogramPoint:
    """A single determined threshold for one ear at one frequency."""

    ear: Ear
    frequency_hz: int
    threshold_db: int


@dataclass(frozen=True)
class Audiogram:
    """A complete, immutable collection of audiogram points.

    ``points`` is stored as a tuple so the value remains hashable and cannot
    be mutated after construction.
    """

    points: Tuple[AudiogramPoint, ...] = field(default_factory=tuple)

    def with_point(self, point: AudiogramPoint) -> "Audiogram":
        """Return a *new* Audiogram with ``point`` appended."""

        return replace(self, points=self.points + (point,))

    def for_ear(self, ear: Ear) -> "Audiogram":
        return Audiogram(tuple(p for p in self.points if p.ear == ear))


@dataclass(frozen=True)
class Presentation:
    """A single tone presentation and the patient's response to it."""

    db_level: int
    responded: bool
    ascending: bool  # True if reached via the +5 dB step


@dataclass(frozen=True)
class HWState:
    """The complete state of an in-progress Hughson-Westlake search.

    The algorithm in :mod:`audiometer.hughson_westlake` consumes a state and
    a response and returns a *new* state. Old states are never mutated.
    """

    ear: Ear
    frequency_hz: int
    current_db: int
    presentations: Tuple[Presentation, ...] = ()
    finished: bool = False
    threshold_db: Maybe[int] = field(default_factory=Nothing)

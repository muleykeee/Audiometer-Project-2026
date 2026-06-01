"""Map / filter / reduce processing of RESPONSE messages.

The YMH 334 brief asks specifically for "RESPONSE messages processed with a
map / filter / reduce chain". Every aggregator in this module is written
that way and works over immutable inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Iterable, Tuple

from audiometer.types import Just, Maybe, Nothing, ResponseEvent

RESPONSE_TOKEN: str = "RESPONSE"


# ---------------------------------------------------------------------------
# Parsing (pure)
# ---------------------------------------------------------------------------


def parse_line(line: str, timestamp_ms: int) -> Maybe[ResponseEvent]:
    """Parse a raw serial line into a :class:`ResponseEvent`.

    The hardware emits ``RESPONSE`` for every button press, optionally
    followed by ``:<id>`` or other tokens. Empty / malformed lines yield
    :class:`Nothing` so the rest of the pipeline can stay pure.
    """

    if line is None:
        return Nothing()
    stripped = line.strip()
    if not stripped:
        return Nothing()
    head = stripped.split(":", 1)[0].upper()
    if head != RESPONSE_TOKEN:
        return Nothing()
    return Just(ResponseEvent(timestamp_ms=timestamp_ms, raw_message=stripped))


# ---------------------------------------------------------------------------
# Map / filter / reduce aggregates
# ---------------------------------------------------------------------------


def to_events(lines: Iterable[Tuple[str, int]]) -> Tuple[ResponseEvent, ...]:
    """Map raw ``(line, timestamp)`` pairs to events, filtering out misses.

    Implemented as an explicit ``map`` followed by ``filter``.
    """

    parsed = map(lambda item: parse_line(item[0], item[1]), lines)
    survivors = filter(lambda m: m.is_just(), parsed)
    return tuple(map(lambda m: m.get_or_else(None), survivors))  # type: ignore[arg-type]


def count_responses(events: Iterable[ResponseEvent]) -> int:
    """Reduce events to a count."""

    return reduce(lambda acc, _ev: acc + 1, events, 0)


def latest_response(events: Iterable[ResponseEvent]) -> Maybe[ResponseEvent]:
    """Reduce events to the one with the largest timestamp."""

    def pick_later(acc: Maybe[ResponseEvent], ev: ResponseEvent) -> Maybe[ResponseEvent]:
        if acc.is_nothing():
            return Just(ev)
        current = acc.get_or_else(ev)
        return Just(ev) if ev.timestamp_ms >= current.timestamp_ms else acc

    return reduce(pick_later, events, Nothing())


def first_response_within(
    events: Iterable[ResponseEvent], window_ms: int, after_ms: int
) -> Maybe[ResponseEvent]:
    """Find the earliest response inside ``[after_ms, after_ms + window_ms]``.

    Built from a filter over the time window followed by a reduce that
    selects the minimum-timestamp event.
    """

    in_window = filter(
        lambda ev: after_ms <= ev.timestamp_ms <= after_ms + window_ms, events
    )

    def pick_earlier(acc: Maybe[ResponseEvent], ev: ResponseEvent) -> Maybe[ResponseEvent]:
        if acc.is_nothing():
            return Just(ev)
        current = acc.get_or_else(ev)
        return Just(ev) if ev.timestamp_ms < current.timestamp_ms else acc

    return reduce(pick_earlier, in_window, Nothing())


def patient_responded(
    events: Iterable[ResponseEvent], window_ms: int, after_ms: int
) -> bool:
    """Boolean shortcut: did the patient press the button in the window?"""

    return first_response_within(events, window_ms, after_ms).is_just()


# ---------------------------------------------------------------------------
# Statistics summary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResponseStats:
    count: int
    first_ms: Maybe[int]
    last_ms: Maybe[int]


def summarise(events: Iterable[ResponseEvent]) -> ResponseStats:
    """Single-pass summary using reduce over an immutable accumulator."""

    materialised = tuple(events)

    def fold(acc: ResponseStats, ev: ResponseEvent) -> ResponseStats:
        first = acc.first_ms if acc.first_ms.is_just() else Just(ev.timestamp_ms)
        if first.is_just() and ev.timestamp_ms < first.get_or_else(ev.timestamp_ms):
            first = Just(ev.timestamp_ms)
        last = acc.last_ms
        if last.is_nothing() or ev.timestamp_ms > last.get_or_else(ev.timestamp_ms):
            last = Just(ev.timestamp_ms)
        return ResponseStats(count=acc.count + 1, first_ms=first, last_ms=last)

    return reduce(fold, materialised, ResponseStats(0, Nothing(), Nothing()))

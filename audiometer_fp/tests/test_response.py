"""Unit tests for the map/filter/reduce response pipeline."""

import pytest

from audiometer.response import (
    count_responses,
    first_response_within,
    latest_response,
    parse_line,
    patient_responded,
    summarise,
    to_events,
)
from audiometer.types import Just, Nothing


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_parse_line_recognises_response_token():
    parsed = parse_line("RESPONSE", 100)
    assert parsed.is_just()
    assert parsed.get_or_else(None).raw_message == "RESPONSE"


def test_parse_line_is_case_insensitive_for_token():
    assert parse_line("response", 100).is_just()
    assert parse_line("Response:1", 100).is_just()


def test_parse_line_rejects_other_tokens():
    assert parse_line("ACK", 100).is_nothing()
    assert parse_line("", 100).is_nothing()
    assert parse_line(None, 100).is_nothing()
    assert parse_line("   ", 100).is_nothing()


def test_parse_line_preserves_extra_payload():
    parsed = parse_line("RESPONSE:42", 100).get_or_else(None)
    assert parsed.raw_message == "RESPONSE:42"


# ---------------------------------------------------------------------------
# Map / filter pipeline
# ---------------------------------------------------------------------------


def test_to_events_filters_invalid_lines():
    raw = [("RESPONSE", 1), ("garbage", 2), ("RESPONSE:1", 3), ("", 4)]
    events = to_events(raw)
    assert len(events) == 2
    assert {e.timestamp_ms for e in events} == {1, 3}


def test_to_events_preserves_order():
    raw = [("RESPONSE", 10), ("RESPONSE", 5), ("RESPONSE", 20)]
    events = to_events(raw)
    assert [e.timestamp_ms for e in events] == [10, 5, 20]


# ---------------------------------------------------------------------------
# Reduce aggregates
# ---------------------------------------------------------------------------


def test_count_responses():
    events = to_events([("RESPONSE", 1), ("RESPONSE", 2), ("RESPONSE", 3)])
    assert count_responses(events) == 3


def test_count_responses_empty():
    assert count_responses([]) == 0


def test_latest_response_picks_max_timestamp():
    events = to_events([("RESPONSE", 5), ("RESPONSE", 100), ("RESPONSE", 50)])
    latest = latest_response(events)
    assert latest.is_just()
    assert latest.get_or_else(None).timestamp_ms == 100


def test_latest_response_on_empty():
    assert latest_response([]) == Nothing()


def test_first_response_within_window():
    events = to_events([("RESPONSE", 50), ("RESPONSE", 200), ("RESPONSE", 1500)])
    hit = first_response_within(events, window_ms=1000, after_ms=100)
    assert hit.is_just()
    assert hit.get_or_else(None).timestamp_ms == 200


def test_first_response_outside_window_is_nothing():
    events = to_events([("RESPONSE", 50), ("RESPONSE", 2000)])
    assert first_response_within(events, window_ms=100, after_ms=200).is_nothing()


def test_patient_responded_returns_bool():
    events = to_events([("RESPONSE", 500)])
    assert patient_responded(events, window_ms=1000, after_ms=0) is True
    assert patient_responded(events, window_ms=10, after_ms=10000) is False


def test_summarise_combines_first_last_count():
    events = to_events([("RESPONSE", 50), ("RESPONSE", 200), ("RESPONSE", 70)])
    s = summarise(events)
    assert s.count == 3
    assert s.first_ms == Just(50)
    assert s.last_ms == Just(200)


def test_summarise_empty():
    s = summarise([])
    assert s.count == 0
    assert s.first_ms == Nothing()
    assert s.last_ms == Nothing()

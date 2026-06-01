"""Side-effecting bridge to the Proteus/ESP32/FPGA hardware.

This is the *only* module in the package that performs real I/O. Everything
else stays pure. The bridge converts raw serial traffic to immutable
:class:`ResponseEvent` values that can be processed by :mod:`audiometer.response`.

``pyserial`` is an optional dependency — install with::

    pip install audiometer-fp[serial]

For tests and demos we provide an in-memory :class:`VirtualPatient` that
mimics the same interface so the pure pipeline can be exercised without
opening a port.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable, List, Tuple

from audiometer.types import Just, Maybe, Nothing, Stimulus


# ---------------------------------------------------------------------------
# Real serial port helpers (side-effecting)
# ---------------------------------------------------------------------------


def open_port(port: str, baudrate: int = 9600, timeout_s: float = 0.1):
    """Open a serial port; returns the Serial object or raises ImportError if
    pyserial is not installed.
    """

    import serial  # local import keeps pyserial optional

    return serial.Serial(port=port, baudrate=baudrate, timeout=timeout_s)


def send_stimulus(serial_port, stimulus: Stimulus) -> None:
    """Send a play command using the wire format shared with the JavaFX GUI.

    The Java ``SerialManager`` (the component wired to the hardware) emits
    ``PLAY,<freq>,<db>``. The Python core was added later, so it is aligned to
    that same comma-separated convention here instead of inventing a second
    format. The ear under test is selected on the GUI side (O / X markers) and
    is not part of the hardware command.
    """

    line = f"PLAY,{stimulus.frequency_hz},{stimulus.level_db}\n"
    serial_port.write(line.encode("ascii"))


def read_line(serial_port) -> Maybe[str]:
    """Return a single line from the port wrapped in Maybe."""

    raw = serial_port.readline()
    if not raw:
        return Nothing()
    try:
        return Just(raw.decode("ascii", errors="replace").strip())
    except Exception:
        return Nothing()


def drain_lines(serial_port, duration_s: float) -> Tuple[Tuple[str, int], ...]:
    """Collect every line emitted by the port for ``duration_s`` seconds.

    The accumulator is built immutably; the function never modifies the
    returned tuple after construction.
    """

    deadline = time.monotonic() + duration_s
    collected: List[Tuple[str, int]] = []
    while time.monotonic() < deadline:
        maybe_line = read_line(serial_port)
        if maybe_line.is_just():
            collected.append(
                (maybe_line.get_or_else(""), int(time.monotonic() * 1000))
            )
    return tuple(collected)


# ---------------------------------------------------------------------------
# Virtual patient (pure — no I/O)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VirtualPatient:
    """Simulated patient whose hearing threshold per frequency is known.

    ``thresholds[frequency]`` is the dB HL at which the simulated patient
    starts responding. ``responds(stim)`` is a pure predicate (deterministic
    if ``jitter_db == 0``).
    """

    thresholds_left: dict
    thresholds_right: dict
    jitter_db: int = 0

    def responds(self, stimulus: Stimulus) -> bool:
        table = (
            self.thresholds_right
            if stimulus.ear.value == "RIGHT"
            else self.thresholds_left
        )
        threshold = table.get(stimulus.frequency_hz, 999)
        return stimulus.level_db >= threshold


def stimulate_virtual_patient(
    stimulus: Stimulus, patient: VirtualPatient
) -> Tuple[Tuple[str, int], ...]:
    """Emit a ``RESPONSE`` line (with a millisecond timestamp) iff the
    virtual patient hears the stimulus."""

    base_ts = int(time.monotonic() * 1000)
    if patient.responds(stimulus):
        return (("RESPONSE", base_ts + 250),)
    return ()


# ---------------------------------------------------------------------------
# Pluggable response oracle (used by hughson_westlake.run_session)
# ---------------------------------------------------------------------------


def make_serial_oracle(serial_port, wait_window_ms: int = 1500) -> Callable[[Stimulus], bool]:
    """Build a ``Stimulus -> bool`` oracle backed by a real serial port.

    The returned callable performs I/O when called, but the algorithm itself
    remains pure.
    """

    def oracle(stim: Stimulus) -> bool:
        from audiometer.response import patient_responded, to_events

        send_stimulus(serial_port, stim)
        raw = drain_lines(serial_port, wait_window_ms / 1000.0)
        events = to_events(raw)
        return patient_responded(events, window_ms=wait_window_ms, after_ms=0)

    return oracle


def make_virtual_oracle(patient: VirtualPatient) -> Callable[[Stimulus], bool]:
    """Build a deterministic oracle for testing and demos."""

    return lambda stim: patient.responds(stim)

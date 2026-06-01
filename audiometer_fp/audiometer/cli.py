"""Command-line driver for the audiometer FP core.

Two modes:

* ``--simulate`` runs a complete Hughson-Westlake battery against a virtual
  patient with known thresholds. Useful for grading, screenshots, and as a
  reference implementation.

* ``--serial <PORT>`` connects to a real (or Proteus-simulated) hardware
  port over jSerialComm / pyserial.

The CLI itself is the only place where side effects happen; everything it
calls comes from the pure core.
"""

from __future__ import annotations

import argparse
import sys
from functools import reduce
from typing import Callable

from audiometer.audiogram import (
    build_audiogram,
    classification_for,
    pta_for,
    to_json_string,
)
from audiometer.hughson_westlake import STANDARD_FREQUENCY_ORDER, run_session
from audiometer.iec60645 import audiogram_complete, state_is_iec_conformant
from audiometer.serial_bridge import VirtualPatient, make_serial_oracle, make_virtual_oracle
from audiometer.types import (
    Audiogram,
    AudiogramPoint,
    Ear,
    Err,
    HWState,
    Just,
    Ok,
)


def run_battery(oracle: Callable, ears=(Ear.RIGHT, Ear.LEFT)) -> Audiogram:
    """Run the standard battery across both ears and all IEC frequencies.

    Uses an immutable fold (reduce) over the (ear, frequency) cross-product
    so that no list is ever appended in place.
    """

    pairs = tuple((ear, f) for ear in ears for f in STANDARD_FREQUENCY_ORDER)

    def consume(audiogram: Audiogram, pair) -> Audiogram:
        ear, freq = pair
        result = run_session(ear, freq, oracle)
        if isinstance(result, Err):
            print(f"!! {ear.value} {freq} Hz: {result.error}", file=sys.stderr)
            return audiogram
        state: HWState = result.value
        iec = state_is_iec_conformant(state)
        if isinstance(iec, Err):
            print(
                f"!! IEC violation at {ear.value} {freq} Hz: {iec.error}",
                file=sys.stderr,
            )
        if state.threshold_db.is_just():
            point = AudiogramPoint(
                ear=ear,
                frequency_hz=freq,
                threshold_db=state.threshold_db.get_or_else(0),
            )
            return audiogram.with_point(point)
        print(f"   {ear.value} {freq} Hz: threshold could not be determined", file=sys.stderr)
        return audiogram

    return reduce(consume, pairs, Audiogram())


def print_report(audiogram: Audiogram) -> None:
    print("=" * 60)
    print("AUDIOMETER FP — TEST REPORT")
    print("=" * 60)
    for ear in (Ear.RIGHT, Ear.LEFT):
        ear_pts = [p for p in audiogram.points if p.ear == ear]
        if not ear_pts:
            print(f"\n[{ear.value}] no data")
            continue
        print(f"\n[{ear.value}]")
        for p in sorted(ear_pts, key=lambda x: x.frequency_hz):
            print(f"  {p.frequency_hz:>5} Hz  ->  {p.threshold_db:+4d} dB HL")
        pta = pta_for(audiogram, ear)
        cls = classification_for(audiogram, ear)
        if pta.is_just():
            print(f"  PTA (4-freq) = {pta.get_or_else(0.0):.1f} dB")
        if cls.is_just():
            print(f"  Classification = {cls.get_or_else('?')}")
    print()
    completeness = audiogram_complete(audiogram)
    if isinstance(completeness, Ok):
        print("Audiogram is IEC 60645-1 complete.")
    else:
        print("Audiogram is incomplete:")
        for missing in completeness.error:
            print(f"  - {missing}")
    print()
    print("JSON export:")
    print(to_json_string(audiogram))


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        prog="audiometer-fp",
        description="Functional-programming core for the audiometer (YMH 334).",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--simulate", action="store_true", help="Run with a virtual patient")
    mode.add_argument("--serial", metavar="PORT", help="Run with a real COM port")
    parser.add_argument("--baud", type=int, default=9600)
    args = parser.parse_args(argv)

    if args.simulate:
        # A made-up patient with mild high-frequency loss on the right ear.
        patient = VirtualPatient(
            thresholds_left={250: 5, 500: 10, 1000: 10, 2000: 15, 4000: 20, 8000: 25},
            thresholds_right={250: 5, 500: 10, 1000: 15, 2000: 25, 4000: 45, 8000: 55},
        )
        oracle = make_virtual_oracle(patient)
    else:
        try:
            from audiometer.serial_bridge import open_port

            port = open_port(args.serial, baudrate=args.baud)
        except ImportError:
            print(
                "error: pyserial is not installed.\n"
                "       install it with 'pip install pyserial' (or 'pip install -e .[serial]'),\n"
                "       or run 'python -m audiometer.cli --simulate' to test without hardware.",
                file=sys.stderr,
            )
            return 2
        except OSError as exc:
            # serial.SerialException is a subclass of OSError; this also covers
            # a missing port, a busy port, or permission problems.
            print(
                f"error: could not open serial port {args.serial!r}: {exc}\n"
                "       check that the port name is correct (e.g. COM3 on Windows,\n"
                "       /dev/ttyUSB0 on Linux), that the device / Proteus COMPIM is\n"
                "       connected, and that no other program is using the port.\n"
                "       to run without hardware use: python -m audiometer.cli --simulate",
                file=sys.stderr,
            )
            return 2
        oracle = make_serial_oracle(port)

    audiogram = run_battery(oracle)
    print_report(audiogram)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

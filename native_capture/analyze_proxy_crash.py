#!/usr/bin/env python3
"""Summarize SHIFT.D3D9ProxyCrash/1 JSONL records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ACCESS_TYPES = {0: "read", 1: "write", 8: "execute"}

# Absolute VAs already backed by decompilation artifacts in this repository.
# These are used only as nearest-known anchors; they do not claim exact
# function extents.
KNOWN_MAIN_FUNCTIONS = (
    (0x0082F3C0, "FUN_0082f3c0", "vehicle-physics-selector-storage-precondition"),
)
KNOWN_FUNCTION_MAX_DELTA = 0x400


def _hex(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    errors = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            errors += 1
            continue
        if isinstance(value, dict):
            events.append(value)
        else:
            errors += 1
    return events, errors


def analyze(events: list[dict[str, Any]], parse_errors: int = 0) -> dict[str, Any]:
    crashes = [
        event for event in events
        if event.get("format") == "SHIFT.D3D9ProxyCrash/1"
    ]
    report: dict[str, Any] = {
        "format": "SHIFT.D3D9ProxyCrashSummary/1",
        "event_count": len(crashes),
        "parse_error_count": parse_errors,
    }
    if not crashes:
        report["diagnosis"] = "malformed-or-empty-crash-log"
        return report

    crash = crashes[-1]
    code = _hex(crash.get("exception_code"))
    access_address = _hex(crash.get("access_address"))
    access_type = crash.get("access_type")
    registers = crash.get("registers")
    if not isinstance(registers, dict):
        registers = {}

    diagnosis = "game-code-exception"
    if code == 0xC0000005:
        diagnosis = "game-code-access-violation"
        if access_address is not None and access_address < 0x10000:
            diagnosis = "game-code-near-null-access-violation"

    main_image = crash.get("main_image")
    if not isinstance(main_image, dict):
        main_image = {}
    base = _hex(main_image.get("base"))
    size = main_image.get("size")
    candidates: list[dict[str, str]] = []
    if base is not None and isinstance(size, int) and size > 0:
        for word in crash.get("stack_words", []):
            address = _hex(word)
            if address is not None and base <= address < base + size:
                candidates.append({
                    "address": f"0x{address:08x}",
                    "rva": f"0x{address - base:08x}",
                })

    exception_address = _hex(crash.get("exception_address"))
    nearest_known_function = None
    if exception_address is not None:
        eligible = [
            (address, name, semantic)
            for address, name, semantic in KNOWN_MAIN_FUNCTIONS
            if address <= exception_address
        ]
        if eligible:
            address, name, semantic = max(eligible, key=lambda item: item[0])
            delta = exception_address - address
            if delta <= KNOWN_FUNCTION_MAX_DELTA:
                nearest_known_function = {
                    "address": f"0x{address:08x}",
                    "name": name,
                    "semantic": semantic,
                    "delta": f"0x{delta:x}",
                }

    report.update({
        "diagnosis": diagnosis,
        "exception_code": crash.get("exception_code"),
        "exception_address": crash.get("exception_address"),
        "exception_rva": crash.get("exception_rva"),
        "access_type": ACCESS_TYPES.get(access_type, access_type),
        "access_address": crash.get("access_address"),
        "registers": registers,
        "main_image_stack_candidates": candidates,
        "nearest_known_function": nearest_known_function,
    })
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("crash_log", type=Path)
    args = parser.parse_args(argv)
    events, errors = read_jsonl(args.crash_log)
    report = analyze(events, errors)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Regression checks for deterministic callback/PM4 join-input archives."""

from __future__ import annotations

import gzip
import importlib.util
import json
import tempfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "export_linux_source1_interrupt_join_inputs_20261028.py"
)
SPEC = importlib.util.spec_from_file_location("join_inputs", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def main() -> None:
    rows = MODULE.join_input_rows({"events": {
        "source1_callback_events": [
            {"source": 1, "wall_clock_epoch_ms": 102, "entry_ordinal": 2},
            {"source": 0, "wall_clock_epoch_ms": 99},
        ],
    }}, [
        {"source": 1, "timestamp_epoch_ms": 101, "ordinal": 7},
        {"source": 1, "timestamp_epoch_ms": 102, "ordinal": 8},
        {"source": 0, "timestamp_epoch_ms": 100},
    ])
    assert [row["timestamp_epoch_ms"] for row in rows] == [101, 102, 102]
    assert [row["record_type"] for row in rows] == [
        "p2_source1_pm4_interrupt",
        "p1_guest_source1_callback",
        "p2_source1_pm4_interrupt",
    ]
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / "joined.jsonl.gz"
        first_hash = MODULE.write_archive(rows, archive)
        first = archive.read_bytes()
        second_hash = MODULE.write_archive(rows, archive)
        assert first_hash == second_hash
        assert first == archive.read_bytes()
        with gzip.open(archive, "rt", encoding="utf-8") as source:
            restored = [json.loads(line) for line in source]
        assert restored == rows

    print("same-run join inputs sort by timestamp and write deterministic JSONL.gz")


if __name__ == "__main__":
    main()

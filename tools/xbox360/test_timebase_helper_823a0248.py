#!/usr/bin/env python3
"""Guard retail timebase-helper evidence and PPC subtraction direction."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_timebase_helper_823a0248_20261024.json").read_text()
)

assert evidence["input"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["input"]["live_elf_sha256"] == (
    "2ffe352bda115285e58661cb5fc5ebe0a8c845d1e7a9ae07bee89e514636c00c"
)

static = evidence["static_basis"]
helper = static["helper"]
assert helper["start"] == "0x823A0248"
assert helper["end_exclusive"] == "0x823A0310"
assert helper["instruction_count"] == 50

r6 = helper["r6_instruction"]
assert r6["bytes_big_endian"] == "7cc85050"
assert r6["canonical_decode"] == "subf r6,r8,r10"
assert r6["architectural_operation"] == "r6 = r10 - r8"
assert "thread_value-record[+0x10]" in r6["crosscheck"]
assert helper["callback"]["explicit_registers"]["r6"].startswith(
    "zero_extend_u64(thread_value) - zero_extend_u64(record[+0x10])"
)

constant = helper["float_constant"]
assert constant["address"] == "0x820FFE40"
assert constant["bytes_big_endian"] == "447a0000"
assert constant["value_float32"] == 1000.0

caller = static["caller_context"]
assert caller["wait_call"] == "0x823A55B8 -> 0x823A0310"
assert caller["finalizer_call"] == "0x823A55DC -> 0x823A0248"

runtime = evidence["runtime_context"]
assert runtime["observations_are_from_separate_runs"] is True
assert "no same-run callback" in runtime["predicate_wait_seen"]
assert any("scheduler" in item for item in evidence["limitations"])

print("retail timebase helper decode, callback subtraction, and caller relation match evidence")

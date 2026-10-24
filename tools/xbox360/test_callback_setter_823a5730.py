#!/usr/bin/env python3
"""Guard the retail callback setter's slot against the queue producer layout."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_callback_setter_823a5730_20261024.json").read_text()
)

assert evidence["input"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["input"]["live_elf_sha256"] == (
    "2ffe352bda115285e58661cb5fc5ebe0a8c845d1e7a9ae07bee89e514636c00c"
)

static = evidence["static_basis"]
setter = static["setter"]
assert setter["start"] == "0x823A5730"
assert setter["end_exclusive"] == "0x823A5738"
assert setter["instruction_count"] == 2
assert setter["instructions"][0]["bytes_big_endian"] == "9083409c"
assert setter["instructions"][0]["operation"] == "stw r4,0x409C(r3)"
assert setter["instructions"][1]["bytes_big_endian"] == "4e800020"

producer = static["deferred_queue_producer"]
assert producer["callback_slot_offset"] == "0x409C"
assert "bctrl" in producer["callback_load"]

runtime = evidence["runtime_context"]["observed_setter_call"]
assert runtime["entry"] == "0x823A5730"
assert runtime["r3_object"] == "0xB7365F00"
assert runtime["r4_value"] == "0x82649B68"
assert "does not prove a later producer hit" in evidence["runtime_context"][
    "conclusion_scope"
]

print("retail callback setter writes the same +0x409C slot used by the deferred producer")

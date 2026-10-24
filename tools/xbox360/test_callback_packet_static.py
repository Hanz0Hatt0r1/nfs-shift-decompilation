#!/usr/bin/env python3
"""Guard the exact-retail callback-pointer stream construction evidence."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_callback_packet_static_20261024.json").read_text()
)

assert evidence["input"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["input"]["live_memory_elf_sha256"] == (
    "2ffe352bda115285e58661cb5fc5ebe0a8c845d1e7a9ae07bee89e514636c00c"
)

static = evidence["static_observation"]
caller = static["caller"]
assert caller["function"] == "0x823A4908"
assert caller["callee"] == "0x823B3598"
assert caller["callsite"] == "0x823A4A3C"
assert caller["register_values_at_call"]["r6"] == "0x823A4758"
caller_bytes = caller["verified_instruction_bytes"]
assert any("3d 60 82 3a" in instruction for instruction in caller_bytes)
assert any("38 cb 47 58" in instruction for instruction in caller_bytes)
assert any("48 00 eb 5d" in instruction for instruction in caller_bytes)

callee = static["callee"]
assert callee["parameter_copy"]["instruction"] == "mr r28,r6"
assert callee["word_stream_write"]["instruction"] == "stwu r28,4(r29)"

runtime = evidence["related_runtime_evidence"]
assert runtime["candidate_function"] == "0x823A4758"
assert runtime["candidate_function_hits"] == 0
assert runtime["source0_consumer_sampled_entries"] > 0
assert runtime["deferred_queue_read_indices"] == [0] * 8
assert runtime["deferred_queue_write_indices"] == [0] * 8

unverified = evidence["interpretation"]["unverified"]
assert any("command type" in item for item in unverified)
assert any("whether this word is a GPU callback" in item for item in unverified)

print("exact-retail callback-pointer stream path and runtime limits match evidence")

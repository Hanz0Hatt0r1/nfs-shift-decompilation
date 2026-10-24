#!/usr/bin/env python3
"""Guard retail callback routing and keep its two completion masks distinct."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_guest_callback_frontier_20261024.json").read_text()
)

assert evidence["input"]["title_id"] == "454108B4"
assert evidence["input"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)

callback = evidence["runtime_observations"]["source0_callback"]
assert callback["retail_function"] == "0x823B37B8"
assert callback["deferred_handler"] == "0x823A4640"
assert callback["logged_entries"] >= 1
assert callback["logged_deferred_handler_entries"] >= 1
assert callback["deferred_handler_guest_return_address"] == "0x823B3844"

queue = evidence["runtime_observations"]["deferred_queue_samples"]
assert len(queue["read_index_values_big_endian"]) == len(
    queue["write_index_values_big_endian"]
)
assert queue["read_index_values_big_endian"] == [0] * 4
assert queue["write_index_values_big_endian"] == [0] * 4
assert queue["first_record_bytes_hex"] == "0000000000000000"

software = evidence["runtime_observations"]["software_queue_helper"]
assert software["predicate_test_mask"] == "0x02"
values = [int(value, 16) for value in software["predicate_byte_samples"]]
assert values == [0x00, 0x14, 0x14, 0x14, 0x14, 0x14]
assert all(value & 0x02 == 0 for value in values)
assert software["samples_with_completion_mask_set"] == 0

packet = json.loads(
    (ROOT / "evidence/xbox360_linux_callback_packet_static_20261024.json").read_text()
)["static_observation"]
assert packet["caller"]["register_values_at_call"]["r6"] == "0x823A4758"
assert packet["callee"]["parameter_copy"]["instruction"] == "mr r28,r6"
assert packet["callee"]["word_stream_write"]["instruction"] == "stwu r28,4(r29)"

gate = json.loads(
    (ROOT / "evidence/xbox360_source0_mmio_gate_refs_20261024.json").read_text()
)
gate_scan = gate["static_scan"]
assert gate_scan["gate_reader"]["function"] == "0x823B37B8"
assert gate_scan["direct_guest_writes_to_0x7fc86544"] == []
assert [
    site["address"]
    for site in gate_scan["high_page_0x7fc8_sites"]
    if site["resolved_address"] == "0x7FC86544"
] == ["0x823B382C"]
assert gate["runtime_crosscheck"]["candidate_producer_hits"] == 0
assert gate["runtime_crosscheck"]["deferred_queue_read_indices"] == [0] * 8
assert gate["runtime_crosscheck"]["deferred_queue_write_indices"] == [0] * 8

print("retail source-0 callback, empty deferred queue, and separate completion mask match")

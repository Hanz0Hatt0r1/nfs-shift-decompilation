#!/usr/bin/env python3
"""Guard retail callback routing and keep its two completion masks distinct."""
import json
import hashlib
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

producer = json.loads(
    (ROOT / "evidence/xbox360_linux_deferred_queue_producer_probe_20261024.json").read_text()
)
static = producer["static_disassembly"]
assert static["elf_sha256"] == (
    "2ffe352bda115285e58661cb5fc5ebe0a8c845d1e7a9ae07bee89e514636c00c"
)
block = static["instructions"]
assert static["range"] == {
    "start": "0x823A4758",
    "end_exclusive": "0x823A4904",
    "instruction_count": 107,
}
assert [int(item["address"], 16) for item in block] == list(
    range(0x823A4758, 0x823A4904, 4)
)
assert static["instruction_bytes_sha256"] == hashlib.sha256(
    bytes.fromhex("".join(item["bytes_big_endian"] for item in block))
).hexdigest()
by_address = {item["address"]: item for item in block}
assert by_address["0x823A4830"]["bytes_big_endian"] == "813f409c"
assert by_address["0x823A4858"]["bytes_big_endian"] == "7d2903a6"
assert by_address["0x823A4868"]["bytes_big_endian"] == "4e800421"
assert by_address["0x823A489C"]["bytes_big_endian"] == "916a40c0"
assert by_address["0x823A48A0"]["bytes_big_endian"] == "93ca40bc"
assert by_address["0x823A48AC"]["bytes_big_endian"] == "917f4140"
assert static["direct_write_inventory"]["full_elf_matching_stw_sites"] == [
    {"address": "0x823A48AC", "source_register": "r11", "base_register": "r31"}
]
assert producer["retail_functions"]["candidate_deferred_queue_producer"][
    "dynamic_hits_during_capture"
] == 0

print("retail callback frontier, queue producer body, and runtime boundary match")

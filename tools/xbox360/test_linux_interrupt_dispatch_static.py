#!/usr/bin/env python3
"""Guard the exact-XEX interrupt routing classification."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_interrupt_dispatch_static_20261026.json").read_text()
)

assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["target"]["live_memory_elf_sha256"] == (
    "2ffe352bda115285e58661cb5fc5ebe0a8c845d1e7a9ae07bee89e514636c00c"
)

dispatch = evidence["static_observations"]["interrupt_dispatcher"]
source_1 = dispatch["source_1_path"]
assert source_1["source_test"] == "0x823B37C8: cmpwi r3,1"
assert source_1["callback_load"] == "0x823B37D4: lwz r10,16(r11)"
assert source_1["indirect_call"] == "0x823B37E8: bctrl"
assert dispatch["source_0_path"]["consumer_call"] == "0x823B3840: bl 0x823A4640"
assert dispatch["direct_branches_to_823A4758"] == []
assert dispatch["direct_branch_scan"]["matches"] == 0

producer = evidence["static_observations"]["deferred_queue_producer"]
assert producer["indirect_callback_slot_load"] == "0x823A4830: lwz r9,16540(r31)"
assert producer["indirect_call"] == "0x823A4868: bctrl"
assert producer["call_condition"] == "object+0x409C callback slot is nonzero"

link = evidence["retail_stream_callback_link"]
assert link["context_pointer_load"] == "0x823B35E4: lwz r10,10900(r11)"
assert link["builder_inputs"]["captured_callback_target"] == "0x823A4758"
assert link["builder_inputs"]["captured_callback_argument"] == "0x00000208"
assert link["callback_record_dwords"]["captured_stream_words"] == [
    "0001057c", "823a4758", "00000208"
]
waits = link["waits_for_callback_record"]
assert [(wait["context_field_offset"], wait["reference_operand"]) for wait in waits] == [
    ("0x14", "0x00000208"),
    ("0x10", "0x823A4758"),
]
assert [wait["packet_address_field"] for wait in waits] == [
    "0x1B964016", "0x1B964012"
]
assert link["interrupt_dispatch_match"]["target_load"] == "0x823B37D4: lwz r10,16(r11)"
assert link["interrupt_dispatch_match"]["argument_load"] == "0x823B37E0: lwz r3,20(r11)"
assert link["interrupt_dispatch_match"]["indirect_call"] == "0x823B37E8: bctrl"
assert link["ordering_in_captured_outer_ib"]["same_execution_run_proven"] is False

runtime = evidence["runtime_crosscheck"]
assert runtime["source_0_callback_hits"] == 99
assert runtime["source_1_callback_hits"] == 0
assert runtime["deferred_consumer_hits"] == 98
assert runtime["producer_0x823A4758_hits"] == 0
assert runtime["retail_queue_head"] <= runtime["retail_wait_target"] <= runtime["retail_queue_tail"]
assert runtime["predicate_byte"] == "0x14"
assert runtime["completion_mask"] == "0x02"
assert runtime["completion_mask_set"] is False

print("exact-XEX interrupt routing and unresolved producer path match")

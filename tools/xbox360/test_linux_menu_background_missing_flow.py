#!/usr/bin/env python3
"""Guard exact-XEX return handling observed for missing menu_background.xml."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_menu_background_missing_flow_20261025.json").read_text()
)

assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["static_artifact"]["sha256"] == (
    "2ffe352bda115285e58661cb5fc5ebe0a8c845d1e7a9ae07bee89e514636c00c"
)
assert evidence["runtime_run"]["guest_memory_modified_by_probe"] is False
assert evidence["runtime_run"]["input_events_sent"] is False

samples = evidence["failed_open_samples"]
assert [sample["guest_path"] for sample in samples] == [
    "d:\\tracks\\_data\\instances\\scenes\\menu_background.xml",
    "d:\\tracks\\_data\\static\\scenes\\menu_background.xml",
]
for sample, hits in zip(samples, ([68, 69], [70, 71])):
    assert sample["ntstatus"] == "0xc000000f"
    assert sample["gdb_entry_hits"] == hits
    assert sample["guest_lr"] == "0x826EF304"
    assert sample["call_chain"][-2:] == ["0x82F7C560", "0x82F7C938"]

flow = evidence["retail_return_flow"]
assert flow["child_call_at"] == "0x82F7CB44"
assert flow["child_result_field_offset"] == 1456
assert flow["parent_return"] == "1 on the observed path"
frontier = evidence["runtime_frontier"]
assert frontier["last_draw_submission_before_first_missing_xml"]["indexed_packets"] == 14
assert frontier["first_missing_xml_local_time"] > frontier["last_draw_submission_before_first_missing_xml"]["local_time"]
assert frontier["draw_submission_entries_after_last_missing_xml"] == 0
assert frontier["later_ntcreatefile_hits"] == [72, 73]
instructions = {item["address"]: item["bytes_big_endian"] for item in evidence["instruction_checks"]}
assert instructions == {
    "0x82F7CB44": "4bfffa1d",
    "0x82F7CB4C": "906605b0",
    "0x82F7CB50": "38a00001",
    "0x82F7CB54": "90a100b0",
    "0x82F7CC00": "806100b0",
    "0x82F7CC14": "4e800020",
}

not_proven = " ".join(evidence["interpretation"]["not_proven"])
assert "main menu" in not_proven
assert "offline race" in not_proven
assert "causality" in not_proven

print("missing menu_background.xml follows the recorded retail child-failure path")

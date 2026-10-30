"""Guard the exact-XEX post-Bink worker-token evidence and claim limits."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_exact_runtime_post_bink_worker_tokens_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-exact-runtime-post-bink-worker-tokens.v1"
assert evidence["target"]["title_id"] == "454108B4"
assert evidence["binaries"]["input_files_hash_verified"] is True
assert evidence["binaries"]["inferior_mapped_hashes_verified"] is False

run = evidence["run"]
assert run["guest_memory_modified_by_probe"] is False
assert run["bink_target_reached"]["progress"] == run["bink_target_reached"]["target"] == 281
assert [item["button"] for item in run["controller_input_sent"]] == ["Start", "A", "Start"]

worker = evidence["retail_worker"]
assert int(worker["counter_manager_guest_object"], 16) + worker["counter_manager_offset"] == int(
    worker["counter_guest_address"], 16
)
assert int(worker["worker_object_guest_address"], 16) + worker["worker_counter_offset"] == int(
    worker["worker_counter_guest_address"], 16
)
assert worker["counter_guest_address"] == worker["worker_counter_guest_address"]
assert worker["matching_worker_entry_count"] == 1811
assert worker["entry_token_counts"] == {"0xC0000000": 1811}
assert worker["stream_addresses"] == ["0xB7368A18", "0xC9630EFC"]
assert [item["counter"] for item in worker["sampled_entries"][:4]] == [
    "0x00000001", "0x00000001", "0x00000000", "0x00000000"
]
assert [item["field72"] for item in worker["sampled_entries"][:4]] == [
    "0xC9624514", "0x00000000", "0xC9624514", "0x00000000"
]
assert worker["first_counter_writes"] == ["0x00000001", "0x00000000", "0xFFFFFFFF"]
assert "only when the current word equals 0xC0000000" in worker["retail_static_crosscheck"][
    "call_condition"
]
assert "only when worker+72 is zero" in worker["retail_static_crosscheck"][
    "decrement_condition"
]

trace = ROOT / run["gdb_trace"]["path"]
assert hashlib.sha256(trace.read_bytes()).hexdigest() == run["gdb_trace"]["sha256"]
not_proven = evidence["interpretation"]["not_proven"]
assert any("expected fence traffic" in claim for claim in not_proven)
assert any("scheduler implementation is defective" in claim for claim in not_proven)
assert any("visible menu" in claim for claim in not_proven)

print("exact-XEX worker-token evidence preserves counter alias, sentinel sequence, and claim limits")

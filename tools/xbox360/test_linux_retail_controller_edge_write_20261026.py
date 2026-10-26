#!/usr/bin/env python3
"""Guard read-only exact-XEX controller edge-write evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_retail_controller_edge_write_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-retail-controller-edge-write.v1"
assert evidence["retail_image"]["sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
run = evidence["run"]
assert run["guest_memory_modified_by_probe"] is False
assert run["runtime_log"]["guest_fault_logged"] is False
assert "guest remained live" in run["termination"]
for key in ("gdb_script", "runner_script"):
    record = run[key]
    actual = hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest()
    assert actual == record["sha256"]

path = evidence["retail_edge_path"]
assert path["controller_object"] == "0xBCAEB260"
assert path["function_hits"] == {
    "sub_82308E60": 1764,
    "sub_8230CD00": 1764,
    "sub_8230D398": 0,
}
assert path["xam_input_get_state_entries"] == path["host_input_get_state_calls"] == 1764
assert path["host_input_return_samples"] == 0
assert [
    (write["button"], write["input_mask"], write["guest_address"], write["old_value"], write["new_value"])
    for write in path["edge_byte_writes"]
] == [
    ("Start", "0x0010", "0xBCAEB2EC", "0x00", "0x80"),
    ("A", "0x1000", "0xBCAEB2F4", "0x00", "0x80"),
]
assert path["watchpoint_backtrace"] == [
    "sub_8230CD00",
    "sub_82308E60",
    "sub_822FA1B0",
    "sub_826C5ED8",
    "sub_822D6EA8",
]
assert evidence["interpretation"]["not_proven"]
assert any("captured no pixels" in item for item in evidence["interpretation"]["not_proven"])

gdb_script = (ROOT / "tools/xbox360/trace_linux_retail_controller_edge_watch.gdb").read_text()
assert "gdb.WP_WRITE" in gdb_script
assert "write_memory" not in gdb_script

print("read-only retail watchpoints confirm Start/A edge-byte writes without claiming frontend entry")

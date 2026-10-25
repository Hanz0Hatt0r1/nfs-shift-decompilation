#!/usr/bin/env python3
"""Guard the observed retail missing-file return path and its limits."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_missing_asset_caller_semantics_20261025.json").read_text()
)

assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["static_artifact"]["sha256"] == (
    "2ffe352bda115285e58661cb5fc5ebe0a8c845d1e7a9ae07bee89e514636c00c"
)
runtime = evidence["runtime_crosscheck"]
assert runtime["failed_path"] == "d:\\tracks\\cameraconfig.xml"
assert runtime["guest_lr"] == "0x826EF304"
assert runtime["guest_call_chain"][:4] == [
    "0x826EF1A0",
    "0x822DD650",
    "0x822DC478",
    "0x822CA1F8",
]

flow = evidence["retail_return_flow"]
assert flow["file_reader"]["maps_open_failure_to"] == "0xfffffffb"
assert flow["resource_reader"]["cleanup_return"] == "0xfffffffb"
assert flow["config_probe"]["nonzero_resource_result_return"] == "0"
assert flow["config_probe_wrapper"]["normalizes_probe_result_to"] == [0, 1]
assert flow["initializer"]["false_return"] == "0"
assert flow["outer_initializer"]["false_result_cleanup_calls"] == [
    "0x82624A28",
    "0x82623EE0",
]
assert flow["outer_initializer"]["continues_initialization_at"] == "0x826252C0"

instructions = {item["address"]: item["bytes_big_endian"] for item in evidence["instruction_checks"]}
assert instructions["0x822DD704"] == "48411a9d"
assert instructions["0x822DD724"] == "3860fffb"
assert instructions["0x822DC5C0"] == "3860fffb"
assert instructions["0x822CA26C"] == "38600000"
assert instructions["0x822CA14C"] == "38600001"
assert instructions["0x822CA15C"] == "38600000"
assert instructions["0x826251B0"] == "38600000"
assert instructions["0x826252AC"] == "4bfff779"
assert instructions["0x826252BC"] == "4bffec25"

not_proven = " ".join(evidence["interpretation"]["not_proven"])
assert "offline race" in not_proven
assert "audio.bff and drivers2.lod" in not_proven

print("retail missing-file sentinel and false-result path match exact ELF evidence")

#!/usr/bin/env python3
"""Guard exact-retail matched-runtime input follow-through evidence."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_depth_resolve_input_followthrough_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-depth-resolve-input-followthrough.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
binaries = evidence["binaries"]
assert binaries["p1_host_sha256"] == (
    "6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b"
)
assert binaries["p2_runtime_sha256"] == (
    "f049d64a46ab04e8d5fcb71800c92d86a5cc6a5fbd38a6b1bf1a623c86398a80"
)
assert binaries["p2_plugin"]["sha256"] == (
    "abc7bf5df779be7dce4fdae719c05c89a35ad8ce222f95b3337478f24bddc402"
)
assert binaries["p2_plugin"]["source_state"].endswith("not claimed merged")
assert binaries["dynamic_resolution"]["unresolved_symbols"] is False

run = evidence["run"]
assert run["duration_seconds"] >= 120
assert run["gdb_instrumented"] is False
assert run["guest_memory_modified_by_probe"] is False
assert run["binary_files_sha256_verified"] is True
assert run["runtime_mapping_independently_captured"] is False
assert "Clean title shutdown was not established" in run["termination"]

controller = run["controller"]
assert len(controller["pulses"]) == 5
assert controller["guest_consumption_observed"] is False
assert [pulse["button"] for pulse in controller["pulses"]] == [
    "A", "Start", "A", "Start", "A"
]

captures = run["target_window_captures"]
assert [capture["elapsed_seconds"] for capture in captures] == [45, 55, 68, 80, 95, 110]
assert [capture["sha256"] for capture in captures] == [
    "eaddc3298cb112d76de48b2edb6f25fece011716c75e956d1675217814caa0b5",
    "e4841f0ffd6812b9005ab7d52dc861e6919621b89dc85b016f6918734f55062d",
    "e33450c6bde6246d2dbb39a7b289705a2dac1bb48ed5f272b6358e8ac39ad7d5",
    "cfe5c1a91dfcca4259eef7349b88f9a5bab1975667333a2467ae196714718d42",
    "843b2d40965678307facdb56f36ca102bba39fb6c5a48ed36e18ac14d1aecfb3",
    "188a5668de11857744dbf7681867eaa225a2284f56188c716d965e18991671d7",
]
assert "disclaimer visible" in captures[0]["observation"]
assert "black" in captures[1]["observation"]
assert "disclaimer visible again" in captures[3]["observation"]
assert "black" in captures[4]["observation"]
assert "disclaimer visible again" in captures[5]["observation"]

logs = run["renderer_logs"]
assert logs["captured_wait_reg_mem_completed"] == 6
assert logs["unsupported_wait_forms"] == 2
assert logs["unresolved_captured_draw_entries"] == 5
assert logs["refresh_failures"] == 1
assert logs["missing_menu_background_xml_opens"] == 4
assert logs["guest_faults"] == 0

comparison = evidence["comparison"]
assert comparison["inputs"] == []
assert "recurring disclaimer/black pattern" in comparison["interpretation"]
assert "guest consumed any uinput pulse" in evidence["interpretation"]["not_proven"][0]
assert "offline-race entry" in evidence["interpretation"]["not_proven"][1]
assert "Keep retail event, queue, and controller semantics unchanged" in evidence["interpretation"]["next_p1_step"]

print("matched exact-retail run completed six waits; recurring frames do not prove input consumption or menu/race progress")

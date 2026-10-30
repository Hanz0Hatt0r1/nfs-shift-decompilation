#!/usr/bin/env python3
"""Guard exact identities and screenshot hashes in the latest retail run evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_resolve_input_frontend_20261025.json").read_text()
)

assert evidence["target"]["sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["p1_host_sha256"] == (
    "6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b"
)
assert evidence["binaries"]["rexglue_runtime_sha256"] == (
    "d15165b314797e56f3eed7810161849dd2f2e3105424f7472e39453deafd9839"
)
assert evidence["binaries"]["p2_renderer_plugin_sha256"] == (
    "1fa623feecb9a7ac6c1cd8d6de61bcabc6a4a01b12dfbeb9b0255fa29945042c"
)

run = evidence["runs"]["input_and_window_trace"]
assert run["runtime_log"]["vulkan_frame_refresh_failures"] == 0
assert run["runtime_log"]["menu_background_xml_open_failures"] == 4
assert run["runtime_log"]["draw_submissions_after_first_xml_failure"] == 0
assert run["input"]["retail_trace"]["successful_non_neutral_user0_samples"] == {
    "0x0010": 6,
    "0x1000": 12,
}
assert len(run["input"]["pulses"]) == 12
assert len(run["window_captures"]["captures"]) == 4

all_captures = [
    evidence["runs"]["presenter_frame640_readback"]["decoded_png"],
    *run["window_captures"]["captures"],
]
for capture in all_captures:
    image = ROOT / capture["path"]
    contents = image.read_bytes()
    assert contents[:8] == b"\x89PNG\r\n\x1a\n"
    assert hashlib.sha256(contents).hexdigest() == capture["sha256"]

assert evidence["interpretation"]["gate_status"] == {
    "X3_retail_rendering": "in_progress",
    "X4_frontend_to_offline_race": "in_progress",
}
assert any("Main-menu entry" in item for item in evidence["interpretation"]["not_proven"])

print("current resolve/input frontend evidence identities and screenshots match")

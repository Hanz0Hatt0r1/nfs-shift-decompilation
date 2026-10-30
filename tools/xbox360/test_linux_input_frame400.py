#!/usr/bin/env python3
"""Check frame-400 readback evidence and preserve its runtime-evidence limits."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence_path = ROOT / "evidence/xbox360_linux_input_frame400_20261025.json"
evidence = json.loads(evidence_path.read_text())
frame = evidence["readback"]

assert evidence["retail_image"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert frame["frame"] == 400
assert (frame["width"], frame["height"]) == (1280, 720)
assert frame["decoded_png"]["path"].startswith("/tmp/")
digest = frame["decoded_png"]["sha256"]
assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
assert frame["decoded_png"]["non_black_rgb_pixels"] == 119808
assert evidence["input"]["events_sent"] == ["Start press/release", "A press/release"]
assert evidence["input"]["retail_xaminput_state_trace_in_this_run"] is False
assert "main menu" in " ".join(evidence["runtime_observations"]["not_proven"])
assert any(
    "Offline race" in claim
    for claim in evidence["runtime_observations"]["not_proven"]
)

print("frame-400 input evidence metadata and menu/race limits match")

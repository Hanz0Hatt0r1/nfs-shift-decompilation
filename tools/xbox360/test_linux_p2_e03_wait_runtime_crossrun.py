#!/usr/bin/env python3
"""Guard exact-XEX evidence for the current P1/P2 Linux cross-run."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_p2_e03_wait_runtime_crossrun_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-p2-e03-wait-runtime-crossrun.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
binaries = evidence["binaries"]
assert binaries["p1_runtime"]["sha256"] == (
    "f43d094797bf30c2e552b244c6ec50e4e69bb0b11fee409e07a812ba74158f78"
)
assert binaries["p2_linux_plugin"]["sha256"] == (
    "1f9e04549f74b6af2506bfc2600dc220e7857d90661b9a57f4a17209e9311f5d"
)

run = evidence["run"]
assert run["guest_memory_written_by_observer"] is False
wait = run["wait_reg_mem"]
assert wait["entered"] is True
assert wait["completed"] is False
assert wait["guest_physical_word"] == "0x1B964004"
assert wait["poll_address"] == "0x1B964006"
assert wait["reference"] == "0x00000001"
assert wait["mask"] == "0xFFFFFFFF"
assert wait["endian_mode"] == 2
assert wait["coher_status_host_waits_completed"] == 4
samples = wait["samples"]
assert [sample["poll"] for sample in samples] == list(range(0, 8000, 1000))
assert all(sample["raw"] == sample["observed"] == "0x00000000" for sample in samples)
assert all(sample["condition"] is False for sample in samples)
assert samples[-1]["elapsed_ms"] == 7735
assert run["verified_game_window_capture"] is False

print("current P1/P2 Linux cross-run reproduces the retail WAIT_REG_MEM frontier")

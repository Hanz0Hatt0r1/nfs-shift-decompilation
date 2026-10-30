#!/usr/bin/env python3
"""Guard the exact-XEX gamepad vtable mapping and its bounded limits."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_gamepad_frontend_consumer_probe_20261025.json")
    .read_text()
)
probe = evidence["controller_vtable_probe"]

assert evidence["retail_image"]["sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert probe["vtable_address"] == "0x8212E5B8"
assert probe["observed_slots"] == {
    "0x54": "0x8230D398",
    "0x98": "0x82308E60",
    "0xBC": "0x828B22B8",
}
assert probe["runtime"]["runtime_sha256"] == evidence["runtime"]["runtime_sha256"]
assert all(len(value) == 64 for key, value in probe["external_probe"].items() if key.endswith("_sha256"))
claims = probe["interpretation"]
assert any("only route" in claim.lower() for claim in claims["not_proven"])
assert any("defective" in claim.lower() for claim in claims["not_proven"])
correlated = evidence["same_run_input_xam_correlation_20261025"]
assert correlated["retail_xex_sha256"] == evidence["retail_image"]["sha256"]
assert correlated["duration_seconds"] >= 90
assert correlated["guest_observations"]["successful_non_neutral_user0_samples"] == {
    "0x1000": 5,
    "0x0010": 13,
}
assert correlated["guest_observations"]["candidate_non_neutral_getter_hits"] == 0
assert correlated["guest_observations"]["candidate_non_neutral_dispatcher_hits"] == 0
assert correlated["guest_observations"]["main_guest_thread_at_interrupt"] == [
    "Core 0/0: Main", "0x823A0310"
]
assert "no pixel readback" in correlated["interpretation"]

print("retail gamepad vtable and same-run input correlation match")

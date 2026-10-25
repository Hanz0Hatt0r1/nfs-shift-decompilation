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

print("retail gamepad vtable slots and bounded dispatch limits match")

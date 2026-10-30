#!/usr/bin/env python3
"""Guard the retail callback-registration snapshot at the first wait."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (
        ROOT
        / "evidence/xbox360_linux_callback_registration_first_wait_20261026.json"
    ).read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-callback-registration-first-wait.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["mapped_hashes_verified_at_wait"] is True

run = evidence["run"]
assert run["registration_hits"] == [
    {
        "setter": "0x823A5730",
        "hits_before_first_wait": 1,
        "object": "0xB7365F00",
        "value": "0x82649B68",
        "caller_return_site": "0x8264D310",
    },
    {
        "setter": "0x823A5728",
        "hits_before_first_wait": 1,
        "object": "0xB7365F00",
        "value": "0x82321198",
        "caller_return_site": "0x8264D320",
    },
]
wait = run["first_wait"]
assert wait["callback_16540_guest_big_endian"] == "0x82649B68"
assert wait["callback_16544_guest_big_endian"] == "0x82321198"
assert wait["producer_0x823A4758_hits"] == 0
assert wait["registered_callback_0x82649B68_hits"] == 0
assert wait["head"] <= wait["target"] <= wait["tail"]
assert evidence["static_generated_code"]["producer_gate"]["indirect_call_site"] == (
    "0x823A486C"
)
assert "preserving the original queue and predicate semantics" in evidence[
    "interpretation"
]["next_p1_step"]

print("retail callback registration is present before the bounded first wait")

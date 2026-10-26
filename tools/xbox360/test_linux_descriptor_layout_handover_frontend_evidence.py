#!/usr/bin/env python3
"""Guard claims in the latest Linux retail run with the P2 descriptor-layout handoff."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (
        ROOT
        / "evidence/xbox360_linux_descriptor_layout_handover_frontend_20261026.json"
    ).read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-descriptor-layout-handover-frontend.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["host"]["mapping_verified"] is True
assert evidence["binaries"]["rexglue_runtime"]["mapping_verified"] is True
assert evidence["binaries"]["gpu_plugin"]["mapping_verified"] is True
assert evidence["binaries"]["gpu_plugin"]["sha256"] == (
    "78d02ba81efa7a8d07e8a1cc6c1b93c22259954dd401b029a02d24bc08fc61d6"
)
assert evidence["binaries"]["ldd_r_unresolved_symbols"] == 0

captures = evidence["run"]["window_captures"]["captures"]
states = [capture["state"] for capture in captures]
assert states[0] == "Language Select with English highlighted"
assert states[1] == "EA logo after A at Language Select"
assert states[2] == "Retail driving-safety disclaimer"
assert "Black viewport" in states[3]
assert states[4] == "Black viewport after 8-second wait"
assert states[5] == "Safety disclaimer visible again after A and Start"
assert len({capture["sha256"] for capture in captures}) == len(captures)

wait = evidence["run"]["gdb_wait_sample"]
assert wait["guest_memory_written"] is False
assert wait["call_chain_top_down"][:4] == [
    "sub_823A0310",
    "sub_823B34A0",
    "sub_823B3850",
    "sub_823A0760",
]
assert wait["object_guest_address"] == "0xB7365F00"
assert int(wait["predicate_byte"], 16) & int(wait["tested_completion_mask"], 16) == 0
assert wait["owner_wait_field"] == "0x00000000"

interpretation = evidence["interpretation"]
assert "caused or prevented" in interpretation["not_proven"][0]
assert "menu" in interpretation["not_proven"][-1].lower()
assert "without changing retail queue or predicate semantics" in interpretation[
    "next_p1_step"
]

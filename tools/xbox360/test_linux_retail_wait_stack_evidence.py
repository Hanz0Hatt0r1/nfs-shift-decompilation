"""Guard the exact-XEX wait-stack snapshot without assigning an unproved cause."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/xbox360_linux_retail_wait_stack_20261025.json"


def test_retail_wait_stack_keeps_guest_state_and_cause_separate():
    evidence = json.loads(EVIDENCE.read_text())
    queue = evidence["retail_queue"]
    stacks = evidence["stacks"]
    interpretation = evidence["interpretation"]

    assert evidence["schema"] == "shift.xbox360.linux-retail-wait-stack.v1"
    assert queue["head"] < queue["tail"]
    assert int(queue["predicate"], 16) & int(queue["tested_completion_mask"], 16) == 0
    assert "sub_823A0310" in stacks["guest_main_thread"]["frames_top_down"][1]
    assert "RingWorkerLoop" in stacks["host_graphics_worker"]["state"]
    assert any("P1 scheduler" in claim for claim in interpretation["not_proven"])
    assert evidence["probe"]["instrumentation"].find("no guest memory was written") >= 0

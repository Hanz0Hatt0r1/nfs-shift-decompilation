#!/usr/bin/env python3
"""Guard the read-only GDB-free retail queue observation."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/xbox360_linux_retail_queue_nogdb_20261025.json"


def test_retail_queue_nogdb_evidence_keeps_guest_semantics_unmodified():
    evidence = json.loads(EVIDENCE.read_text())

    assert evidence["schema"] == "shift.xbox360.linux.retail-queue-nogdb-probe.v1"
    assert evidence["target"]["sha256"] == (
        "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
    )
    assert evidence["binaries"]["host"]["sha256"] == (
        "6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b"
    )
    assert evidence["run"]["instrumentation"].startswith("No GDB or breakpoints.")
    assert "no guest-memory writes" in evidence["run"]["instrumentation"]
    assert evidence["run"]["duration_seconds"] >= 75

    queue = evidence["retail_queue"]
    stalled = queue["unchanged_final_state"]
    assert stalled["stable_sample_count"] == 38
    assert stalled["last_elapsed_seconds"] - stalled["first_elapsed_seconds"] >= 40
    assert stalled["head"] == 4329
    assert stalled["tail"] == 4339
    assert stalled["pending_cursor_units"] == 10
    assert int(stalled["predicate"], 16) & int(queue["tested_completion_mask"], 16) == 0

    runtime = evidence["runtime_log"]
    assert runtime["guest_fault_entries"] == 0
    assert runtime["vulkan_frame_refresh_failures"] == 0
    assert runtime["indexed_draw_submission_entries"] == 105
    assert runtime["copy_convert_entries"] == 940
    assert runtime["menu_background_open_failures"] == 4

    assert len(evidence["game_window_captures"]) == 3
    limitations = [item.lower() for item in evidence["interpretation"]["not_proven"]]
    assert any("main-menu entry" in item for item in limitations)
    assert any("offline-race entry" in item for item in limitations)

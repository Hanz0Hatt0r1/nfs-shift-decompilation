#!/usr/bin/env python3
"""Guard the exact-XEX input/interrupt follow-through evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_linux_retail_input_interrupt_followthrough_20261026.json").read_text())
assert evidence["schema"] == "shift.xbox360.linux-retail-input-interrupt-followthrough.v1"
assert evidence["target"]["xex_sha256"] == "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
assert evidence["binaries"]["p2_plugin"]["source_state"] == "local P2 scratch-writeback build; not claimed merged"
run = evidence["run"]
assert 60 <= run["duration_seconds"] <= 61
assert run["guest_memory_modified_by_probe"] is False
assert run["controller"]["candidate_button_dispatcher"]["hits"] == 0
masks = {row["buttons"] for row in run["controller"]["non_neutral_controller_update_samples"]}
assert masks == {"0x1000", "0x0010"}
assert run["interrupt_path"]["source1_interrupt_hits"] == 1125
assert run["interrupt_path"]["deferred_producer"]["hits"] == 890
assert run["interrupt_path"]["registered_callback"]["hits"] == 890
assert evidence["gpu_frontier"]["captured_wait"]["completed"] is True
assert evidence["gpu_frontier"]["unresolved_captured_draw_entries"] == 16
assert evidence["interpretation"]["not_proven"]
assert not any("main menu reached" in item.lower() or "race reached" in item.lower() for item in evidence["interpretation"]["observed"])
print("retail input, source-1 callback, and unresolved renderer evidence boundaries match")

#!/usr/bin/env python3
"""Guard exact-XEX input retest observations without claiming menu entry."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_retail_disclaimer_input_retest_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-retail-disclaimer-input-retest.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
run = evidence["run"]
assert run["guest_memory_modified_by_probe"] is False
assert run["binaries"]["gpu_plugin"]["source_state"].startswith("Local Process 2")
controller = run["controller"]
assert len(controller["pulses"]) == 9
assert controller["pulses"][4] == {
    "at_seconds": 90,
    "button": "A",
    "xinput_mask": "0x1000",
}

captures = run["target_window_captures"]
assert [capture["elapsed_seconds"] for capture in captures] == [85.024, 95.011, 125.040]
assert "disclaimer visible" in captures[0]["observation"]
assert "black" in captures[1]["observation"]
assert "no main-menu UI" in captures[2]["observation"]

logs = run["runtime_logs"]
assert logs[0]["failed_menu_background_xml_opens"] == 4
assert logs[0]["unique_unresolved_draw_reasons"] == 16
assert sum(log["captured_indexed_draw_submissions"] for log in logs) == 1286

interpretation = evidence["interpretation"]
assert any("not proof" in item for item in interpretation["inference"])
assert any("main menu or an offline race" in item for item in interpretation["not_proven"])
assert "Treat the A-to-black-frame transition as a lead" in interpretation["next_p1_step"]

print("retail disclaimer input retest records a scene change without claiming menu entry")

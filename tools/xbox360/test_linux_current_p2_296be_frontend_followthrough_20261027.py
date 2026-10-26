"""Guard the latest exact-retail P2 Linux frontend follow-through evidence."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (
        ROOT
        / "evidence/xbox360_linux_current_p2_296be_frontend_followthrough_20261027.json"
    ).read_text()
)

assert evidence["schema"] == (
    "shift.xbox360.linux-current-p2-296be-frontend-followthrough.v1"
)
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["sources"]["p2_renderer"]["source_commit"] == (
    "296be17faee91f79ef5036d1b282423295d172ac"
)
assert evidence["sources"]["p2_renderer"]["plugin_sha256"] == (
    "0ccbeab62a7a592fda942083c83172a1536a89246c2ffc903aa2188f106ac7b0"
)
assert evidence["run"]["termination"].startswith(
    "The capture harness sent SIGINT"
)
assert evidence["run"]["controller"]["guest_observation_proven"] is False
assert [capture["observation"] for capture in evidence["run"]["target_window_captures"]][
    0
].startswith("Retail SHIFT logo and loading")
assert all(
    "menu UI" in capture["observation"]
    for capture in evidence["run"]["target_window_captures"][1:]
)
log = evidence["run"]["runtime_log"]
assert log["accepted_copy_convert_records"] == 935
assert log["completed_coher_status_host_wait_records"] == 8804
assert log["vulkan_frame_refresh_failures"] == 8
assert "mixed 4x-to-1x depth/stencil" in log[
    "vulkan_frame_refresh_failure_reason"
]
assert log["missing_menu_background_xml_opens"] == 4
interpretation = evidence["interpretation"]
assert any("eight frame-refresh failures" in item for item in interpretation["supported"])
assert any("not established as causal" in item for item in interpretation["supported"])
assert any("main-menu entry" in item for item in interpretation["not_proven"])
assert "Keep P1 retail wait and input semantics unchanged" in interpretation[
    "next_step"
]

print("latest exact-XEX run remains at the renderer-blocked black-frame frontier")

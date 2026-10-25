#!/usr/bin/env python3
"""Guard static retail Bink section and callsite facts without overclaiming runtime hits."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_bink_guest_path_20261025.json").read_text())

assert evidence["input"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
sections = {s["name"]: s for s in evidence["static_image"]["sections"]}
bink = sections["BINK"]
bink_start = int(bink["virtual_address"], 16)
bink_end = bink_start + int(bink["virtual_size"], 16)
assert (bink_start, bink_end) == (0x83064C00, 0x83073F54)
assert sections[".XBMOVIE"]["virtual_size"] == "0x8"

calls = {int(c["call_site"], 16): c for c in evidence["static_image"]["code_call_sites"]}
for site, target in ((0x82678FEC, 0x830670B0), (0x826790FC, 0x83067920)):
    item = calls[site]
    word = int(item["instruction_big_endian"], 16)
    assert word >> 26 == 18 and word & 1  # PPC bl
    disp = word & 0x03FFFFFC
    if disp & 0x02000000:
        disp -= 0x04000000
    decoded_target = disp if word & 2 else site + disp
    assert decoded_target == target == int(item["target"], 16)
    assert bink_start <= target < bink_end

registered = set(evidence["runtime_translation"]["generated_and_registered_guest_functions"])
assert {"0x830670B0", "0x83067920", "0x830655F8", "0x83067C20"} <= registered
probe = evidence["runtime_translation"]["p1_breakpoint_probe"]
assert probe["bink_entry_hits"] == 0
assert probe["status"].startswith("superseded by ")
live_probe = evidence["runtime_translation"]["p1_live_entry_probe_20261025"]
assert live_probe["duration_seconds"] == 40
assert live_probe["stop"].startswith("The harness sent SIGINT")
assert set(live_probe["hit_counts"]) == {"0x823A0998", *registered}
assert all(count > 0 for count in live_probe["hit_counts"].values())
assert "does not demonstrate decoded pixels" in live_probe["interpretation"]
manager_probe = evidence["runtime_translation"]["p1_manager_callback_probe_20261025"]
assert manager_probe["duration_seconds"] == 40
assert manager_probe["manager"]["slot_count"] == 4
assert manager_probe["manager"]["dispatch_356_hits"] == 4
assert manager_probe["manager"]["dispatch_376_hits"] == 4
targets = manager_probe["callback_targets"]
assert set(targets) == {"0x83068250", "0x83068608"}
assert all(target["indirect_guest_calls"] == 4 for target in targets.values())
assert all(target["manager_indices"] == [0, 1, 2, 3] for target in targets.values())
assert "rules out an empty/unregistered" in manager_probe["interpretation"]
assert "does not show that callback execution produced pixels" in manager_probe["interpretation"]
assert evidence["external_runtime_report"]["raw_pread_trace_or_log_hash_provided"] is False
assert "not_proven" in evidence["interpretation"]

print("retail Bink section, guest callsites, generated entries, and runtime-evidence limits match")

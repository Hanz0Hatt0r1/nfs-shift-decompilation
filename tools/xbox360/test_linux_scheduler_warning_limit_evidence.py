#!/usr/bin/env python3
"""Guard exact-XEX evidence for the ReXGlue scheduler warning limit."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_scheduler_warning_limit_20261025.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux.scheduler-warning-limit.v1"
assert evidence["target"]["sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
change = evidence["source_change"]
assert re.fullmatch(r"[0-9a-f]{40}", change["commit"])
assert re.fullmatch(r"[0-9a-f]{64}", change["file_sha256"])
assert "pull/534" in change["pull_request"]

run = evidence["run"]
assert run["duration_seconds"] >= 40
assert run["loaded_libraries_verified_from_proc_maps"] is True
log = run["runtime_log"]
assert log["too_few_processor_cores_warning_count"] == 1
assert log["accepted_copy_convert_entries"] == 935
assert log["guest_faults"] == log["sigsegv"] == log["sigbus"] == 0

comparison = evidence["comparison"]
assert comparison["baseline_warning_count"] == 8196
assert comparison["baseline_same_host_xex_and_plugin"] is True
assert "does not prove" in comparison["interpretation"]

print("exact-XEX scheduler warning-limit evidence is internally consistent")

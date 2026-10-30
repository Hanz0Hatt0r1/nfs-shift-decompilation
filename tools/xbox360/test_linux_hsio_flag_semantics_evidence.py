#!/usr/bin/env python3
"""Guard the retail HSIO flag's inverted boolean semantics."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_hsio_flag_semantics_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-retail-hsio-flag-semantics.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)

static = evidence["static_retail_analysis"]
assert static["import"]["library"] == "xboxkrnl.exe"
assert static["import"]["ordinal"] == "0x01C6"
assert static["import"]["resolved_name"] == "VdIsHSIOTrainingSucceeded"
assert static["global"]["writer_store"] == "0x823B9FD0"
assert static["global"]["reader_sites"] == ["0x823A53C0", "0x823B3444"]
assert static["software_completion_guard"]["requires_global_nonzero"] is True

probe = evidence["runtime_probe"]
assert probe["guest_memory_written"] is False
api_result = probe["observations"]["guest_r3_after_import"]
global_value = int(probe["observations"]["global_after_retail_store"], 16)

# PPC cntlzw followed by rlwinm r11,r11,27,31,31 computes (r3 == 0).
def retail_flag(api_result: int) -> int:
    cntlzw = 32 if api_result == 0 else 32 - api_result.bit_length()
    rotated = ((cntlzw << 27) | (cntlzw >> 5)) & 0xFFFFFFFF
    return rotated & 1


assert retail_flag(0) == 1
assert retail_flag(1) == 0
assert retail_flag(api_result) == global_value
assert global_value == 0
assert probe["observations"]["context_r11_at_store"] == global_value
assert evidence["interpretation"]["global_zero_is_expected_for_api_success"] is True
assert evidence["interpretation"]["software_fallback_enabled"] is False
assert evidence["interpretation"]["global_zero_proves_gpu_event_failure"] is False
assert evidence["interpretation"]["global_zero_identifies_missing_producer"] is False

print("retail HSIO flag evidence preserves the inverted predicate semantics")

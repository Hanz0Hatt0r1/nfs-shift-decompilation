#!/usr/bin/env python3
"""Keep exact-XEX ring alias evidence from conflating virtual and physical mappings."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_guest_ring_physical_virtual_alias_20261025.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-guest-ring-physical-virtual-alias.v1"
assert evidence["input"]["retail_xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
mapping = evidence["mapping_observation"]
assert int(mapping["descriptor_virtual_host"], 16) == (
    int(mapping["guest_virtual_base_host"], 16)
    + int(mapping["descriptor_guest_virtual"], 16)
)
assert int(mapping["descriptor_physical_host"], 16) == (
    int(mapping["guest_physical_base_host"], 16)
    + int(mapping["descriptor_guest_physical"], 16)
)
writes = mapping["write_sequence"]
assert mapping["physical_alias_writes_observed"] == 360
assert writes["first_value"] == "0x00000005"
assert writes["last_value"] == "0x000002D7"
assert writes["step"] == "0x2"
assert writes["values_monotonic"] is True
assert writes["virtual_alias_equal_on_every_watchpoint_hit"] is True

samples = mapping["retail_wait_samples"]
assert len(samples) == 4
assert all(sample["descriptor_virtual"] == sample["descriptor_physical"] for sample in samples)
assert [int(sample["tail"]) for sample in samples] == [21, 81, 161, 695]
assert all(sample["predicate"] == "0x14" for sample in samples)
assert evidence["capture"]["guest_memory_modified_by_probe"] is False
assert "No P1 guest-wait" in evidence["adjudication"]["p1_conclusion"]

print("physical EVENT_WRITE_SHD stores are visible through the exact guest virtual ring alias")

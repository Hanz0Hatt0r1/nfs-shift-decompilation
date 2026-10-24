#!/usr/bin/env python3
"""Guard exact-retail queue-gate evidence against fabricated completion."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_queue_completion_conditions_20261024.json").read_text()
)

assert evidence["input"]["title_id"] == "454108B4"
assert evidence["input"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)

static = evidence["static_basis"]
helper = static["software_queue_helper"]
assert helper["function"] == "0x823B33A0"
assert helper["completion_predicate_byte_offset"] == "0x2ABD"
assert helper["completion_mask"] == "0x02"
assert "global 0x831B3820 nonzero" in helper["setter_guard"]

producer = static["global_producer"]
assert producer["import"] == "VdIsHSIOTrainingSucceeded"
assert producer["retail_transform"].endswith("produces global value 0")
assert producer["rexglue_source"].endswith("returns 1")
assert producer["upstream_behavior"].endswith("returns 1")

probe = evidence["runtime_probe"]
assert probe["guest_memory_mutated"] is False
samples = probe["sampling"]
indices = samples["helper_sample_indices"]
assert len(indices) >= 25 and indices == sorted(set(indices))
assert indices[-1] >= 1500
assert set(samples["global_0x831B3820_values"]) == {0}
assert samples["queue_tail_object_0x2A9C_first"] < samples[
    "queue_tail_object_0x2A9C_last_sample"
]
assert samples["queue_tail_object_0x2A9C_last_sample"] >= 3000
assert samples["predicate_hardware_watchpoint_write_count"] >= 1000
predicate_values = [int(value, 16) for value in samples["predicate_hardware_watchpoint_values"]]
assert predicate_values
assert all(value & 0x02 == 0 for value in predicate_values)

limits = evidence["interpretation"]["not_proven"]
assert any("EVENT_WRITE_SHD destination/value" in item for item in limits)
assert any("menu" in item and "race" in item for item in limits)

print("retail queue gate matches the exact-XEX helper and observed runtime; no bit was fabricated")

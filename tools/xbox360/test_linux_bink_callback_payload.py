#!/usr/bin/env python3
"""Guard the retail Bink callback payload trace and its bounded claims."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence_path = ROOT / "evidence/xbox360_linux_bink_callback_payload_20261025.json"
trace_path = ROOT / "tools/xbox360/trace_bink_callback_buffer.gdb"
evidence = json.loads(evidence_path.read_text())
guest = evidence["guest_observation"]
probe = evidence["probe"]

assert evidence["schema"] == "shift.xbox360.linux-bink-callback-payload.v1"
assert evidence["target"]["retail_xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["host_runtime"]["runtime_override_sha256"] == (
    "7335f654806f073a733f2207f00832919a0d13010131420275396a61cfd1092b"
)
assert evidence["host_runtime"]["gpu_plugin_sha256"] == (
    "42f338bc48e144e9dbc70dd208f9a169f437b506d1c338832896c1a6b83b7f10"
)
assert probe["guest_memory_modified"] is False
assert probe["callback_compare_hits"] == 4
assert probe["post_copy_callback_hits"] == 3
assert probe["artifacts"]["gdb_script"]["sha256"] == hashlib.sha256(
    trace_path.read_bytes()
).hexdigest()

assert guest["context_register_offsets"] == {
    "r3": 0,
    "r4": 32,
    "r5": 40,
    "r6": 48,
    "lr": 256,
}
assert guest["source_guest_address"] == "0x7018F6F0"
samples = guest["samples"]
assert len(samples) == 4
for sample in samples:
    width, height = sample["dimensions"]
    assert sample["element_count"] == 6
    assert sample["copy_bytes"] == width * height * 4
    assert len(sample["source_first_24_bytes"]) == 48
    if "destination_after_first_24_bytes" in sample:
        assert sample["destination_after_first_24_bytes"] == sample["source_first_24_bytes"]

assert [sample["copy_bytes"] for sample in samples] == [48, 24, 24, 48]
assert samples[0]["destination_after_captured"] is False
not_proven = guest["interpretation"]["not_proven"]
assert any("decoded Bink pixel buffer" in claim for claim in not_proven)
assert any("offline race" in claim for claim in not_proven)

trace = trace_path.read_text()
assert "break sub_82BA8DA8 if *(unsigned int*)($rdi+256)==0x82ba92b8" in trace
assert "break sub_82B9C770 if *(unsigned int*)($rdi+256)==0x82ba8e28" in trace
assert "REX_STORE" not in trace

print("retail Bink callback payload evidence matches the captured metadata-copy path")

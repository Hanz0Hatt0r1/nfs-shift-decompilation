#!/usr/bin/env python3
"""Validate the bounded retail callback-stream frontier record."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_callback_stream_targeted_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-callback-stream-targeted.v1"
assert evidence["target"]["sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)

stream = evidence["runs"]["retail_stream_emission"]
assert stream["runtime_sha256_mapped"] == (
    "127181adbfb99b65e9d1a8f1d6aed12308e1cf320b86067588ad421f17eda68e"
)
assert stream["observed"]["r6_callback_value"].lower() == "0xffffffff823a4758"
assert stream["observed"]["guest_lr"] == "0x823A4A40"
words = stream["observed"]["output_prefix_words_big_endian"]
assert words[4] == words[23] == "823a4758"
assert stream["renderer_sha256_mapped"] != (
    "dec875819cc6146c820838ac8ee52b45b90b83c7bb70d4d521ecc9dcdb4c6ee1"
)

current = evidence["runs"]["current_p2_pair_frontier"]
assert current["runtime_sha256_mapped"] == (
    "127181adbfb99b65e9d1a8f1d6aed12308e1cf320b86067588ad421f17eda68e"
)
assert current["renderer_sha256_mapped"] == (
    "dec875819cc6146c820838ac8ee52b45b90b83c7bb70d4d521ecc9dcdb4c6ee1"
)
assert current["observed"]["initialization_hits"] == 1
assert current["observed"]["producer_0x823A4758_hits"] == 0
assert current["observed"]["registered_callback_0x82649B68_hits"] == 0
assert current["observed"]["producer_and_callback_breakpoints_installed"] is True
assert current["observed"]["runtime_and_renderer_mapping_hashes_read_from_proc_maps"] is True

assert any("older renderer plugin" in item for item in evidence["interpretation"]["not_proven"])
assert any("offline-race progress" in item for item in evidence["interpretation"]["not_proven"])

correlated = evidence["runs"]["current_p2_pair_stream_and_ring_trace"]
assert correlated["binaries"]["runtime_and_plugin_same_as_current_pair_frontier"] is True
assert correlated["guest_memory_modified"] is False
assert correlated["stream_emission"]["guest_stream_address"] == "0xA95D05D0"
stream_words = correlated["stream_emission"]["captured_first_32_dwords_big_endian"]
assert len(stream_words) == 32
assert stream_words[4] == stream_words[23] == "823a4758"
observed = correlated["observed"]
assert observed["ring_wake_events"] == observed["ring_snapshot_events"] == observed["ring_complete_events"]
assert observed["ring_complete_events"] > 0
assert observed["producer_0x823A4758_breakpoint_hits"] == 0
assert observed["registered_callback_0x82649B68_breakpoint_hits"] == 0
assert any("particular GPU ring snapshots" in item for item in correlated["interpretation"]["not_proven"])

print("retail callback stream and current-pair frontier evidence are internally consistent")

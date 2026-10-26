#!/usr/bin/env python3
"""Guard startup-to-WAIT CPU write-watch evidence for the exact retail XEX."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_p2_wait_word_startup_cpu_watch_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-p2-wait-word-startup-cpu-watch.v1"
assert evidence["target"]["title_id"] == "454108B4"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
binaries = evidence["binaries"]
assert binaries["host_sha256"] == (
    "610d8f53750cef76ecf3f003c7e6e5e1b9873f9068579b43429a819815a0122a"
)
assert binaries["p1_runtime_sha256"] == (
    "f43d094797bf30c2e552b244c6ec50e4e69bb0b11fee409e07a812ba74158f78"
)
assert binaries["p2_linux_plugin_sha256"] == (
    "0837991a5d2ac07c81e5fc352be9b5520d3d7d2b224547d7af76c95d5e985e01"
)
run = evidence["run"]
assert run["guest_memory_written_by_probe"] is False
setup = run["watch_setup"]
assert setup["when"] == "immediately after rex::memory::Memory::Initialize returned"
assert setup["watchpoint_count"] == 4
assert setup["sampled_physical_word_before_arming"] == "0x00000000"
assert {item["address"] for item in setup["host_aliases"]} == {
    "0x21B964004",
    "0x1BB964004",
    "0x1DB964004",
    "0x1FB963004",
}
wait = run["wait"]
assert wait["operation"] == "WAIT_REG_MEM"
assert wait["guest_word"] == "0x1B964004"
assert wait["poll_address"] == "0x1B964006"
assert wait["reference"] == "0x00000001"
assert wait["byte_offset"] == "0x49C"
assert wait["packet_hex"] == "c0043c00000000131b96400600000001ffffffff00000100"
watch = run["write_watch"]
script = (ROOT / watch["script"]["path"]).read_bytes()
assert hashlib.sha256(script).hexdigest() == watch["script"]["sha256"]
assert watch["target_wait_decode_observed"] is True
assert watch["cpu_write_stops"] == 0
assert watch["post_wait_observation_min_seconds"] >= 75
assert "clean title shutdown was not observed" in watch["termination"]
cleanup = watch["temporary_guest_memory_file"]
assert cleanup["open_or_mapped_references_at_cleanup"] == 0
assert cleanup["unlinked_after_reference_check"] is True
assert evidence["interpretation"]["not_proven"] == [
    "GPU/DMA writes, cache visibility, or accesses through an unobserved alias.",
    "That the early-RPTR candidate matches Xbox hardware semantics.",
    "Main-menu entry, offline-race entry, or clean title shutdown."
]

print("startup CPU watch evidence is consistent; retail wait semantics remain unchanged")

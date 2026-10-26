#!/usr/bin/env python3
"""Keep the read-only retail queue trace on verified guest addresses."""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
trace = (ROOT / "tools/xbox360/trace_guest_gpu_queue.gdb").read_text()

required = (
    "break sub_823B37B8",
    "set $source = *(unsigned int*)$ctx",
    "source1_callback_record hit=%d object=%#x record=%#x target=%#x argument=%#x lr=%#llx",
    "set $record_raw = *(unsigned int*)($base+$object+0x2a94)",
    "set $target_raw = *(unsigned int*)($base+$record_ptr+0x10)",
    "set $argument_raw = *(unsigned int*)($base+$record_ptr+0x14)",
    "mapped_gpu_plugin pid=%d path=%s sha256=%s segments=%d",
    "open(\"/proc/%d/maps\" % pid",
    "hashlib.sha256(plugin_file.read()).hexdigest()",
    "set $object = *(unsigned int*)($ctx+32)",
    "set $read_raw = *(unsigned int*)($base+$object+0x413c)",
    "set $write_raw = *(unsigned int*)($base+$object+0x4140)",
    "set $predicate = *(unsigned char*)($base+$object+0x2abd)",
    "break sub_823A4640",
    "break sub_823B33A0",
    "set $head_ptr_raw = *(unsigned int*)($base+$object+0x2a90)",
    "set $tail_raw = *(unsigned int*)($base+$object+0x2a9c)",
    "set $global_raw = *(unsigned int*)($base+0x831b3820)",
    "set $flag = *(unsigned char*)($base+$object+0x2abc)",
    "break sub_823B34A0",
    "break sub_823A4758",
    "break sub_82649B68",
    "The consumer's guest LR (0x823B3844) below is the direct taken-path proof.",
    "lr=%#llx",
    "The trace reads guest RAM through rsi and never writes it.",
)
for token in required:
    assert token in trace, f"queue trace lost required read-only probe: {token}"
assert "base+0x7fc86544" not in trace, "MMIO must not be read as ordinary guest RAM"

evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_guest_gpu_queue_trace_20261024.json").read_text()
)
assert evidence["input"]["retail_xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
guest = evidence["guest_observations"]
assert guest["source0_interrupt"]["hits"] == 3207
assert guest["deferred_consumer"]["guest_lr_samples"] == ["0x823B3844"]
assert guest["deferred_queue_indices"]["reported_values"] == {
    "read": [0],
    "write": [0],
}
predicate_values = [int(value, 16) for value in guest["software_queue_predicate"]["reported_values"]]
assert all((value & 0x02) == 0 for value in predicate_values)
assert guest["unreached_candidates"]["deferred_queue_producer_0x823A4758_hits"] == 0
assert evidence["readback"]["non_black_rgb_pixels"] == 0

for line in trace.splitlines():
    stripped = line.strip()
    assert not stripped.startswith(("set *(unsigned", "set *(char", "set {")), (
        "queue trace must not assign through a guest-memory address: " + stripped
    )

print("guest queue trace preserves the MMIO boundary and locks current retail callback evidence")

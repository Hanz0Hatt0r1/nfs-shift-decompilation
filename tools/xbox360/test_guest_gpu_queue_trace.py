#!/usr/bin/env python3
"""Keep the read-only retail queue trace on verified guest addresses."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
trace = (ROOT / "tools/xbox360/trace_guest_gpu_queue.gdb").read_text()

required = (
    "break sub_823B37B8",
    "set $source = *(unsigned int*)$ctx",
    "set $object = *(unsigned int*)($ctx+32)",
    "set $gate_raw = *(unsigned int*)($base+0x7fc86544)",
    "set $read_raw = *(unsigned int*)($base+$object+0x413c)",
    "set $write_raw = *(unsigned int*)($base+$object+0x4140)",
    "set $predicate = *(unsigned char*)($base+$object+0x2abd)",
    "break sub_823A4640",
    "break sub_823B34A0",
    "break sub_823A4758",
    "break sub_82649B68",
    "gate_bit0=%u",
    "The trace reads guest RAM through rsi and never writes it.",
)
for token in required:
    assert token in trace, f"queue trace lost required read-only probe: {token}"

for line in trace.splitlines():
    stripped = line.strip()
    assert not stripped.startswith(("set *(unsigned", "set *(char", "set {")), (
        "queue trace must not assign through a guest-memory address: " + stripped
    )

print("guest queue trace samples the retail gate, queue indices, and predicate without guest writes")

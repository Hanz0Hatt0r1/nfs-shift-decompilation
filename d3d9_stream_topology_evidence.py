"""Source-backed STREAM grouping topology from FUN_00854e70."""
from __future__ import annotations
from typing import Any

FORMAT = "SHIFT.D3D9StreamTopologyEvidence/1"
FUNCTION = "FUN_00854e70"
GROUP_STRIDE = 0x14

def _has(text: str, *needles: str, start: int = 0) -> bool:
    return all(text.find(n, start) >= 0 for n in needles)

def _any(text: str, *needles: str, start: int = 0) -> bool:
    return any(text.find(n, start) >= 0 for n in needles)

def _line(text: str, needle: str, start: int) -> int | None:
    p = text.find(needle, start)
    return None if p < 0 else text.count("\n", 0, p) + 1

def analyze_d3d9_stream_topology(source: str | bytes) -> dict[str, Any]:
    raw = source if isinstance(source, bytes) else str(source).encode()
    text = raw.decode("utf-8", errors="replace")
    start = text.find(f"undefined4 __fastcall {FUNCTION}")
    if start < 0:
        return {"format": FORMAT, "function": FUNCTION, "status": "not-found",
                "source": {"kind": "shift-exe-c", "bytes": len(raw)},
                "inputs": {}, "grouping": {},
                "semantic_links": {"stream_id_to_group": {"status":"not-proven"},
                                    "type_to_group_byte_size": {"status":"not-proven"}},
                "meb_property_mapping": {"status":"not-proven"}}

    inputs = {
        "stream_array": {"status": "observed" if _has(text,
            "*(int *)(local_28 + 0x44)",
            "*(int *)(*(int *)(local_28 + 0x44) + local_70 * 4)", start=start) else "not-found"},
        "type_ordinal_array": {"status": "observed" if _has(text,
            "*(int *)(local_28 + 0x3c)",
            "FUN_00853c20(*(int *)(*(int *)(local_28 + 0x3c) + local_70 * 4))",
            "*(int *)(uVar3 + 0x70)",
            "FUN_00853c20(*(int *)(*(int *)(uVar3 + 0x70) + local_8 * 4))", start=start) else "not-found"},
        "usage_ordinal_array": {"status": "observed" if _any(text,
            "*(int *)(local_28 + 0x40)", "FUN_00853c40((int)local_6c)",
            "FUN_00853c40(local_5c)", "*(int *)(uVar3 + 0x74)", start=start) else "not-found"},
        "channel_array": {"status": "observed" if _any(text,
            "*(int *)(local_28 + 0x48)", "*(int *)(*(int *)(local_28 + 0x48) + iVar12 * 4)",
            "*(undefined1 *)(*(int *)(local_28 + 0x48)", "*(int *)(uVar3 + 0x78)",
            "*(undefined1 *)(*(int *)(uVar3 + 0x78) + uVar11 * 4)", start=start) else "not-found"},
    }

    stream_group = _any(text,
        "*(ushort **)(*(int *)(local_28 + 0x44) + local_70 * 4)",
        "*(int *)(*(int *)(uVar3 + 0x6c) + local_8 * 4) * 0x14", start=start)
    pointer_array = _any(text,
        "*(int *)(*(int *)((int)local_38 * 0x10 + 8 + *(int *)(iVar15 + 0x24)) + local_24 * 4)",
        "*(int *)(*(int *)(iVar1 + 8 + *(int *)((int)this + 0x24)) + *piVar7 * 4)", start=start)
    count = _any(text, "local_24 = local_24 + 1;", "*piVar7 = *piVar7 + 1;",
                 "*(int *)((int)local_38 * 0x10 + 4 + *(int *)(iVar15 + 0x24))", start=start)
    size = _any(text, "DAT_00b8eef0", "local_40 = local_40 +",
                "*piVar7 = *piVar7 + *(int *)(&DAT_00b8eef0", start=start)

    required = all([
        v["status"] == "observed" for v in inputs.values()
    ]) and stream_group and pointer_array and count and size

    return {
        "format": FORMAT,
        "function": FUNCTION,
        "status": "observed" if required else "not-proven",
        "source": {"kind":"shift-exe-c","bytes":len(raw),
                   "line_count":len(text.splitlines()),"function_line":start+1},
        "inputs": inputs,
        "grouping": {
            "group_array_base": "this + 0x24",
            "group_stride": GROUP_STRIDE,
            "stream_to_group_index": "observed" if stream_group else "not-found",
            "record_pointer_array": "observed" if pointer_array else "not-found",
            "count_increment": "observed" if count else "not-found",
            "byte_size_accumulation": "observed" if size else "not-found",
            "field_offsets": {"byte_size":0,"element_count":4,"record_pointer_array":8},
        },
        "source_lines": {
            "function": start+1,
            "stream_group_index": _line(text, "local_8 * 4) * 0x14", start),
            "record_pointer_write": _line(text, "local_24 * 4)", start),
            "byte_size_increment": _line(text, "DAT_00b8eef0", start),
        },
        "semantic_links": {
            "stream_id_to_group": {"status":"observed" if stream_group else "not-proven",
                "detail":"Stream selects a per-stream group with 0x14-byte stride."},
            "type_to_group_byte_size": {"status":"observed" if size else "not-proven",
                "detail":"resolved Type indexes DAT_00b8eef0 and its byte size is accumulated per stream group."},
            "stream_group_to_record_pointer": {"status":"observed" if pointer_array else "not-proven"},
        },
        "meb_property_mapping": {"status":"not-proven",
            "reason":"the recovered stream topology contains no literal MEB property ids"},
    }


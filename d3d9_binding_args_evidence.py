"""Extract source-backed argument semantics for D3D9 mesh resource binding.

FUN_00854da0 dispatches SetStreamSource with:
  Stream = param_2
  VertexBuffer = *(param_1[9] + 0xc + param_3 * 0x10)
  OffsetInBytes = 0
  Stride = result of the stream-type +0x1c getter

FUN_00854e10 dispatches SetIndices with the recovered index-buffer pointer.

The report records argument forwarding and source storage paths. It does not
infer MEB properties or assign a specific D3D9 call to a particular runtime
frame.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.D3D9BindingArgsEvidence/1"
STREAM_FUNCTION = "FUN_00854da0"
INDEX_FUNCTION = "FUN_00854e10"


def _function_body(source: str, function: str) -> tuple[int | None, int | None, str]:
    lines = source.splitlines()
    start = None
    for index, line in enumerate(lines, 1):
        if re.search(rf"\b{re.escape(function)}\(", line):
            start = index
            break
    if start is None:
        return None, None, ""
    depth = 0
    seen = False
    body: list[str] = []
    for index in range(start, len(lines) + 1):
        line = lines[index - 1]
        body.append(line)
        depth += line.count("{")
        depth -= line.count("}")
        if "{" in line:
            seen = True
        if seen and depth == 0:
            return start, index, "\n".join(body)
    return start, None, "\n".join(body)


def analyze_d3d9_binding_args(source: str) -> dict[str, Any]:
    if not isinstance(source, str):
        raise TypeError("source must be str")

    stream_start, stream_end, stream_body = _function_body(source, STREAM_FUNCTION)
    index_start, index_end, index_body = _function_body(source, INDEX_FUNCTION)

    stream_slot = "+400" in stream_body or "+ 400" in stream_body or "+ 0x190" in stream_body
    stream_number = "piVar2,param_2" in stream_body
    vertex_buffer = "param_1[9] + 0xc + param_3 * 0x10" in stream_body
    zero_offset = ",0,uVar3)" in stream_body or ",0,uVar3);" in stream_body
    stride_getter = "uVar3 = (**(code **)(*param_1 + 0x1c))();" in stream_body
    index_slot = "+ 0x1a0" in index_body
    index_buffer = "*(undefined4 *)(param_2 * 0x50 + 0x40 + *(int *)(param_1 + 0x2c))" in index_body

    return {
        "format": FORMAT,
        "status": "observed"
        if stream_start is not None
        and index_start is not None
        and all((stream_slot, stream_number, vertex_buffer, zero_offset, stride_getter, index_slot, index_buffer))
        else "not-proven",
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(source.encode("utf-8")),
            "line_count": len(source.splitlines()),
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        },
        "stream_source": {
            "function": STREAM_FUNCTION,
            "line_start": stream_start,
            "line_end": stream_end,
            "api_method": "IDirect3DDevice9::SetStreamSource",
            "vtable_slot": 100,
            "vtable_byte_offset": "0x190",
            "arguments": {
                "stream": {"status": "observed" if stream_number else "not-found", "expression": "param_2"},
                "vertex_buffer": {
                    "status": "observed" if vertex_buffer else "not-found",
                    "expression": "param_1[9] + 0xc + param_3 * 0x10",
                },
                "offset_in_bytes": {"status": "observed" if zero_offset else "not-found", "value": 0},
                "stride": {
                    "status": "observed" if stride_getter else "not-found",
                    "expression": "result of (*param_1 + 0x1c) getter",
                },
            },
        },
        "index_source": {
            "function": INDEX_FUNCTION,
            "line_start": index_start,
            "line_end": index_end,
            "api_method": "IDirect3DDevice9::SetIndices",
            "vtable_slot": 104,
            "vtable_byte_offset": "0x1a0",
            "arguments": {
                "index_buffer": {
                    "status": "observed" if index_buffer else "not-found",
                    "expression": "*(undefined4 *)(param_2 * 0x50 + 0x40 + *(int *)(param_1 + 0x2c))",
                },
            },
        },
        "semantic_links": {
            "stream_arguments_to_device": {
                "status": "observed"
                if all((stream_slot, stream_number, vertex_buffer, zero_offset, stride_getter))
                else "not-proven",
                "detail": "the recovered stream wrapper forwards stream, buffer, zero byte offset and computed stride",
            },
            "index_argument_to_device": {
                "status": "observed" if index_slot and index_buffer else "not-proven",
                "detail": "the recovered index wrapper forwards the stored index-buffer pointer",
            },
        },
        "evidence_boundary": {
            "runtime_resource_identity": "not-supplied",
            "draw_frame_identity": "not-proven",
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "detail": "Binding argument evidence does not establish MEB 460/461 -> Type linkage.",
        },
    }


def analyze_d3d9_binding_args_file(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    return analyze_d3d9_binding_args(
        source_path.read_text(encoding="utf-8")
    )

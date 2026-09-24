"""Extract source-backed D3D9 render API boundary evidence.

This layer records the recovered mesh primitive setup wrappers and the
IDirect3DDevice9 vtable slots they dispatch through:
  declaration -> SetVertexDeclaration (87 / 0x15c)
  vertex stream -> SetStreamSource (100 / 0x190)
  index buffer -> SetIndices (104 / 0x1a0)
  indexed draw -> DrawIndexedPrimitive (82 / 0x148)

The report intentionally distinguishes direct source observations from the
external API slot identity and does not infer MEB property mappings.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.D3D9RenderApiBoundaryEvidence/1"
SOURCE_FUNCTIONS = {
    "declaration": "FUN_00854d30",
    "stream_source": "FUN_00854da0",
    "index_source": "FUN_00854e10",
}
API_METHODS = {
    "declaration": {
        "method": "IDirect3DDevice9::SetVertexDeclaration",
        "slot": 87,
        "byte_offset": 0x15C,
    },
    "stream_source": {
        "method": "IDirect3DDevice9::SetStreamSource",
        "slot": 100,
        "byte_offset": 0x190,
    },
    "index_source": {
        "method": "IDirect3DDevice9::SetIndices",
        "slot": 104,
        "byte_offset": 0x1A0,
    },
    "draw_indexed": {
        "method": "IDirect3DDevice9::DrawIndexedPrimitive",
        "slot": 82,
        "byte_offset": 0x148,
    },
}
RENDER_FUNCTION = "FUN_0084b9a0"


def _function_body(source: str, function: str) -> tuple[int | None, int | None, str]:
    lines = source.splitlines()
    start = None
    for index, line in enumerate(lines, 1):
        match = re.search(rf"\b{re.escape(function)}\s*\(", line)
        if not match:
            continue
        tail = "\n".join(lines[index - 1:min(len(lines), index + 2)])
        if "{" in tail and (";" not in line or line.rstrip().endswith("{")):
            start = index
            break
    if start is None:
        return None, None, ""
    depth = 0
    seen = False
    body = []
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

def _observation(body: str, byte_offset: int, bodies: dict[str, str] | None = None) -> dict[str, Any]:
    hex_token = f"+ 0x{byte_offset:x}"
    decimal_token = f"+ {byte_offset}"
    matched_as = None
    if hex_token in body:
        matched_as = "hex"
    elif decimal_token in body:
        matched_as = "decimal"
    else:
        for callee in re.findall(r"\bFUN_[0-9A-Fa-f]+\s*\(", body):
            name = callee.split("(", 1)[0].strip()
            callee_body = (bodies or {}).get(name, "")
            if hex_token in callee_body or decimal_token in callee_body:
                matched_as = "delegated"
                break
    return {
        "status": "observed" if matched_as else "not-found",
        "vtable_byte_offset": f"0x{byte_offset:x}",
        "source_offset_representation": matched_as,
    }


def analyze_d3d9_render_api_boundary(source: str) -> dict[str, Any]:
    if not isinstance(source, str):
        raise TypeError("source must be str")

    observations: dict[str, Any] = {}
    for key, function in SOURCE_FUNCTIONS.items():
        start, end, body = _function_body(source, function)
        api = API_METHODS[key]
        obs = _observation(body, api["byte_offset"], {fn: _function_body(source, fn)[2] for fn in SOURCE_FUNCTIONS.values()})
        obs.update({
            "function": function,
            "line_start": start,
            "line_end": end,
            "api_method": api["method"],
            "vtable_slot": api["slot"],
        })
        observations[key] = obs

    render_start, render_end, render_body = _function_body(source, RENDER_FUNCTION)
    mesh_order = [
        ("apply_declaration", SOURCE_FUNCTIONS["declaration"]),
        ("set_stream_source", SOURCE_FUNCTIONS["stream_source"]),
        ("set_index_source", SOURCE_FUNCTIONS["index_source"]),
    ]
    positions = {
        label: render_body.find(function)
        for label, function in mesh_order
    }
    order_ok = all(
        positions[label] >= 0 for label, _ in mesh_order
    ) and positions["apply_declaration"] < positions["set_stream_source"] < positions["set_index_source"]

    draw_matches = [
        index
        for index, line in enumerate(source.splitlines(), 1)
        if "(*piVar" in line and "+ 0x148)" in line
    ]

    observations["mesh_render_setup_order"] = {
        "status": "observed" if order_ok else "not-proven",
        "function": RENDER_FUNCTION,
        "line_start": render_start,
        "line_end": render_end,
        "calls": [
            {"stage": label, "function": function}
            for label, function in mesh_order
        ],
        "order": [label for label, _ in mesh_order],
    }
    observations["draw_indexed_dispatch"] = {
        "status": "observed" if draw_matches else "not-found",
        "api_method": API_METHODS["draw_indexed"]["method"],
        "vtable_slot": API_METHODS["draw_indexed"]["slot"],
        "vtable_byte_offset": f"0x{API_METHODS['draw_indexed']['byte_offset']:x}",
        "source_line_numbers": draw_matches[:32],
        "occurrence_count": len(draw_matches),
    }

    setup_ok = all(
        observations[key]["status"] == "observed"
        for key in ("declaration", "stream_source", "index_source", "mesh_render_setup_order")
    )
    draw_ok = observations["draw_indexed_dispatch"]["status"] == "observed"

    return {
        "format": FORMAT,
        "status": "observed" if setup_ok and draw_ok else "not-proven",
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(source.encode("utf-8")),
            "line_count": len(source.splitlines()),
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        },
        "api_methods": API_METHODS,
        "observations": observations,
        "semantic_links": {
            "declaration_to_stream_setup": {
                "status": "observed" if setup_ok else "not-proven",
                "detail": "mesh render path applies declaration, then binds stream sources and index source",
            },
            "render_setup_to_draw": {
                "status": "observed" if setup_ok and draw_ok else "not-proven",
                "detail": "source contains the recovered declaration/stream/index setup boundary and an indexed-draw dispatch",
            },
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "detail": "D3D9 render API boundary does not establish MEB 460/461 -> Type linkage.",
        },
    }


def analyze_d3d9_render_api_boundary_file(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    return analyze_d3d9_render_api_boundary(
        source_path.read_text(encoding="utf-8")
    )

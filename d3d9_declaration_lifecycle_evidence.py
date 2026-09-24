"""Extract the direct source call-chain for the recovered D3D9 declaration lifecycle.

The evidence joins these source-observed edges:
  mesh construction -> FUN_008587e0
  FUN_008587e0 -> FUN_00830f80
  FUN_00830f80 -> CreateVertexDeclaration
  render path -> FUN_00854d30
  FUN_00854d30 -> FUN_0082e510
  FUN_0082e510 -> SetVertexDeclaration

This is a static source call-chain report. It does not claim that one specific
runtime frame exercised every edge, and it does not infer MEB property mappings.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.D3D9DeclarationLifecycleEvidence/1"

EDGES = {
    "mesh_constructor_to_loader": {
        "caller": "FUN_0085aac0",
        "callee": "FUN_008587e0",
        "detail": "mesh construction path dispatches to the file-backed CPrimitiveType loader",
    },
    "loader_to_canonicalizer": {
        "caller": "FUN_008587e0",
        "callee": "FUN_00830f80",
        "detail": "loader passes the built declaration-record buffer to the canonicalizer",
    },
    "canonicalizer_to_create": {
        "caller": "FUN_00830f80",
        "callee": "CreateVertexDeclaration",
        "detail": "canonicalizer dispatches through D3D9 vtable slot 86 / 0x158",
    },
    "render_to_apply_wrapper": {
        "caller": "FUN_0084b9a0",
        "callee": "FUN_00854d30",
        "detail": "mesh render path applies the stored declaration before stream/index setup",
    },
    "apply_wrapper_to_bind_wrapper": {
        "caller": "FUN_00854d30",
        "callee": "FUN_0082e510",
        "detail": "ApplyVertexDeclaration forwards the stored declaration object",
    },
    "bind_wrapper_to_set_vertex_declaration": {
        "caller": "FUN_0082e510",
        "callee": "SetVertexDeclaration",
        "detail": "wrapper dispatches through D3D9 vtable slot 87 / 0x15c",
    },
}


def _function_body(source: str, function: str) -> tuple[int | None, int | None, str]:
    lines = source.splitlines()
    pattern = re.compile(
        rf"(?m)^[^\n{{}}]*\b{re.escape(function)}\s*\([^;\n]*\)\s*(?:\n[^\n{{}}]*)?\{{"
    )
    match = pattern.search(source)
    if match is None:
        return None, None, ""
    start = source.count("\n", 0, match.start()) + 1
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

def _function_call_status(body: str, function: str) -> bool:
    return bool(re.search(rf"\b{re.escape(function)}\s*\(", body))


def _api_slot_status(body: str, byte_offset: int) -> bool:
    return f"+ 0x{byte_offset:x}" in body or f"+ {byte_offset}" in body

def analyze_d3d9_declaration_lifecycle(source: str) -> dict[str, Any]:
    if not isinstance(source, str):
        raise TypeError("source must be str")

    bodies: dict[str, str] = {}
    ranges: dict[str, dict[str, int | None]] = {}
    for function in {
        "FUN_0085aac0",
        "FUN_008587e0",
        "FUN_00830f80",
        "FUN_0084b9a0",
        "FUN_00854d30",
        "FUN_0082e510",
    }:
        start, end, body = _function_body(source, function)
        bodies[function] = body
        ranges[function] = {"line_start": start, "line_end": end}

    edge_results: dict[str, Any] = {}

    edge = EDGES["mesh_constructor_to_loader"]
    ctor_body = bodies["FUN_0085aac0"]
    edge_results["mesh_constructor_to_loader"] = {
        "status": "observed" if _function_call_status(ctor_body, edge["callee"]) else "not-found",
        "caller": edge["caller"],
        "callee": edge["callee"],
        "detail": edge["detail"],
    }

    edge = EDGES["loader_to_canonicalizer"]
    loader_body = bodies["FUN_008587e0"]
    edge_results["loader_to_canonicalizer"] = {
        "status": "observed" if _function_call_status(loader_body, edge["callee"]) else "not-found",
        "caller": edge["caller"],
        "callee": edge["callee"],
        "detail": edge["detail"],
    }

    edge = EDGES["canonicalizer_to_create"]
    canonicalizer_body = bodies["FUN_00830f80"]
    edge_results["canonicalizer_to_create"] = {
        "status": "observed" if _api_slot_status(canonicalizer_body, 0x158) else "not-found",
        "caller": edge["caller"],
        "callee": edge["callee"],
        "detail": edge["detail"],
        "vtable_slot": 86,
        "vtable_byte_offset": "0x158",
    }

    edge = EDGES["render_to_apply_wrapper"]
    render_body = bodies["FUN_0084b9a0"]
    edge_results["render_to_apply_wrapper"] = {
        "status": "observed" if _function_call_status(render_body, edge["callee"]) else "not-found",
        "caller": edge["caller"],
        "callee": edge["callee"],
        "detail": edge["detail"],
    }

    edge = EDGES["apply_wrapper_to_bind_wrapper"]
    apply_body = bodies["FUN_00854d30"]
    edge_results["apply_wrapper_to_bind_wrapper"] = {
        "status": "observed" if _function_call_status(apply_body, edge["callee"]) else "not-found",
        "caller": edge["caller"],
        "callee": edge["callee"],
        "detail": edge["detail"],
    }

    edge = EDGES["bind_wrapper_to_set_vertex_declaration"]
    bind_body = bodies["FUN_0082e510"]
    edge_results["bind_wrapper_to_set_vertex_declaration"] = {
        "status": "observed" if _api_slot_status(bind_body, 0x15C) else "not-found",
        "caller": edge["caller"],
        "callee": edge["callee"],
        "detail": edge["detail"],
        "vtable_slot": 87,
        "vtable_byte_offset": "0x15c",
    }

    all_observed = all(
        result["status"] == "observed"
        for result in edge_results.values()
    )

    return {
        "format": FORMAT,
        "status": "observed" if all_observed else "not-proven",
        "source": {
            "kind": "shift-exe-c",
            "bytes": len(source.encode("utf-8")),
            "line_count": len(source.splitlines()),
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        },
        "functions": ranges,
        "edges": edge_results,
        "lifecycle": [
            "mesh_constructor_to_loader",
            "loader_to_canonicalizer",
            "canonicalizer_to_create",
            "render_to_apply_wrapper",
            "apply_wrapper_to_bind_wrapper",
            "bind_wrapper_to_set_vertex_declaration",
        ],
        "evidence_boundary": {
            "static_source_call_chain": "observed" if all_observed else "not-proven",
            "runtime_frame_identity": "not-supplied",
            "specific_mesh_instance": "not-proven",
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "detail": "The declaration lifecycle call chain does not establish MEB 460/461 -> Type linkage.",
        },
    }


def analyze_d3d9_declaration_lifecycle_file(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    return analyze_d3d9_declaration_lifecycle(
        source_path.read_text(encoding="utf-8")
    )

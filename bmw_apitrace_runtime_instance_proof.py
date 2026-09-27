#!/usr/bin/env python3
"""Prove D3D9 declaration/buffer object identity at BMW target draws from apitrace evidence.

This proof is deliberately narrower than the full runtime shader/material gate:
it establishes that the declaration object selected by SetVertexDeclaration and
the vertex/index buffer objects selected at the same DrawIndexedPrimitive are
tracked to creation instances without pointer-reuse ambiguity.

It does not infer declaration bytes, MEB identity, shader permutation, constants,
or texture identity from geometry alone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWM3APITRACERuntimeDrawInstanceProof/1"
DEFAULT_PRIMITIVE_COUNTS = (28, 50, 192, 204, 2098, 2462)


def _as_pointer(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value and value != "NULL" else None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _stable_sha(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _candidate_for_primitive(
    row: Mapping[str, Any],
    primitive_count: int,
    *,
    target_vertex_count: int,
    target_vb_pointer: str | None,
    target_ib_pointer: str | None,
) -> dict[str, Any]:
    state = row.get("state") or {}
    resources = row.get("resources") or {}
    declaration = resources.get("vertex_declaration") or {}
    vertex_buffer = resources.get("vertex_buffer") or {}
    index_buffer = resources.get("index_buffer") or {}
    state_declaration = state.get("vertex_declaration") or {}

    draws = [
        draw
        for draw in (row.get("draws") or [])
        if _int(draw.get("num_vertices")) == target_vertex_count
        and _int(draw.get("prim_count")) == primitive_count
    ]
    draw = draws[0] if draws else None

    checks: dict[str, bool] = {
        "draw_observed": draw is not None,
        "declaration_pointer_present": _as_pointer(
            declaration.get("pointer")
        )
        is not None,
        "declaration_state_pointer_matches": (
            _as_pointer(declaration.get("pointer"))
            == _as_pointer(state_declaration.get("pointer"))
        ),
        "declaration_instance_tracked": declaration.get("same_instance") is True,
        "vertex_buffer_pointer_present": _as_pointer(
            vertex_buffer.get("pointer")
        )
        is not None,
        "vertex_buffer_instance_tracked": vertex_buffer.get("same_instance")
        is True,
        "index_buffer_pointer_present": _as_pointer(
            index_buffer.get("pointer")
        )
        is not None,
        "index_buffer_instance_tracked": index_buffer.get("same_instance")
        is True,
    }

    if target_vb_pointer is not None:
        checks["target_vertex_buffer_pointer_match"] = (
            _as_pointer(vertex_buffer.get("pointer")) == target_vb_pointer
        )
    if target_ib_pointer is not None:
        checks["target_index_buffer_pointer_match"] = (
            _as_pointer(index_buffer.get("pointer")) == target_ib_pointer
        )

    declaration_creation = declaration.get("creation") or {}
    vertex_creation = vertex_buffer.get("creation") or {}
    index_creation = index_buffer.get("creation") or {}

    binding_call = _int(state_declaration.get("call"))
    draw_call = _int((draw or {}).get("call"))
    declaration_creation_call = _int(declaration_creation.get("call"))
    vertex_binding_call = _int(vertex_buffer.get("binding_call"))
    vertex_creation_call = _int(vertex_creation.get("call"))
    index_binding_call = _int(index_buffer.get("binding_call"))
    index_creation_call = _int(index_creation.get("call"))

    checks["declaration_binding_before_draw"] = (
        binding_call is not None
        and draw_call is not None
        and binding_call < draw_call
    )
    checks["declaration_creation_before_binding"] = (
        declaration_creation_call is not None
        and binding_call is not None
        and declaration_creation_call < binding_call
    )
    checks["vertex_binding_before_draw"] = (
        vertex_binding_call is not None
        and draw_call is not None
        and vertex_binding_call < draw_call
    )
    checks["vertex_creation_before_binding"] = (
        vertex_creation_call is not None
        and vertex_binding_call is not None
        and vertex_creation_call < vertex_binding_call
    )
    checks["index_binding_before_draw"] = (
        index_binding_call is not None
        and draw_call is not None
        and index_binding_call < draw_call
    )
    checks["index_creation_before_binding"] = (
        index_creation_call is not None
        and index_binding_call is not None
        and index_creation_call < index_binding_call
    )

    ready = all(checks.values())
    instance_material = {
        "primitive_count": primitive_count,
        "draw_call": draw_call,
        "declaration": {
            "pointer": _as_pointer(declaration.get("pointer")),
            "binding_call": binding_call,
            "creation_call": declaration_creation_call,
        },
        "vertex_buffer": {
            "pointer": _as_pointer(vertex_buffer.get("pointer")),
            "binding_call": vertex_binding_call,
            "creation_call": vertex_creation_call,
            "offset_bytes": _int(vertex_buffer.get("offset_bytes")),
            "stride": _int(vertex_buffer.get("stride")),
        },
        "index_buffer": {
            "pointer": _as_pointer(index_buffer.get("pointer")),
            "binding_call": index_binding_call,
            "creation_call": index_creation_call,
        },
    }
    instance_material["identity_sha256"] = _stable_sha(instance_material)

    return {
        "geometry_key_sha256": row.get("geometry_key_sha256"),
        "primitive_count": primitive_count,
        "first_draw_call": _int(row.get("first_draw_call")),
        "draw": draw,
        "checks": checks,
        "ready": ready,
        "instance": instance_material,
    }


def build_report(
    unique_geometry: Mapping[str, Any],
    *,
    primitive_counts: tuple[int, ...] = DEFAULT_PRIMITIVE_COUNTS,
) -> dict[str, Any]:
    if unique_geometry.get("format") != "SHIFT.APITRACEUniqueBMWGeometry/1":
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["input:invalid-format"],
            "input_format": unique_geometry.get("format"),
        }

    scan = unique_geometry.get("scan") or {}
    target_vertex_count = _int(scan.get("target_vertex_count")) or 3550
    target_vb_pointer = _as_pointer(scan.get("target_vertex_buffer_pointer"))
    target_ib_pointers = {
        int(key): _as_pointer(value)
        for key, value in (scan.get("target_index_buffer_pointers") or {}).items()
        if _int(key) is not None
    }

    rows = list(unique_geometry.get("geometry") or [])
    candidates: dict[str, list[dict[str, Any]]] = {}
    blocking_reasons: list[str] = []

    for primitive_count in primitive_counts:
        rows_for_primitive = [
            row
            for row in rows
            if primitive_count in {
                _int(value) for value in (row.get("primitive_counts") or [])
            }
        ]
        evaluated = [
            _candidate_for_primitive(
                row,
                primitive_count,
                target_vertex_count=target_vertex_count,
                target_vb_pointer=target_vb_pointer,
                target_ib_pointer=target_ib_pointers.get(primitive_count),
            )
            for row in rows_for_primitive
        ]
        candidates[str(primitive_count)] = evaluated
        ready_candidates = [item for item in evaluated if item["ready"]]
        if not ready_candidates:
            if not evaluated:
                blocking_reasons.append(
                    f"primitive:{primitive_count}:candidate-not-found"
                )
            else:
                failed = set()
                for item in evaluated:
                    failed.update(
                        name for name, ok in item["checks"].items() if not ok
                    )
                blocking_reasons.append(
                    f"primitive:{primitive_count}:checks-failed:"
                    + ",".join(sorted(failed))
                )

    ready = not blocking_reasons and all(
        any(item["ready"] for item in candidates[str(primitive)])
        for primitive in primitive_counts
    )

    selected = []
    for primitive in primitive_counts:
        ready_rows = [item for item in candidates[str(primitive)] if item["ready"]]
        if ready_rows:
            selected.append(ready_rows[0]["instance"])

    unique_instances = sorted(
        {row["identity_sha256"] for row in selected}
    )

    return {
        "format": FORMAT,
        "status": "proven" if ready else ("partial" if rows else "not-found"),
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
        "input": {
            "format": unique_geometry.get("format"),
            "source": unique_geometry.get("source"),
            "target_vertex_count": target_vertex_count,
            "target_vertex_buffer_pointer": target_vb_pointer,
            "target_index_buffer_pointers": dict(
                sorted(target_ib_pointers.items())
            ),
        },
        "primitive_counts": list(primitive_counts),
        "candidates": candidates,
        "selected_instances": selected,
        "unique_instance_count": len(unique_instances),
        "evidence_boundary": {
            "draw_local_declaration_identity": (
                "observed" if ready else "not-proven"
            ),
            "draw_local_vertex_buffer_identity": (
                "observed"
                if ready
                and all(
                    any(item["ready"] for item in candidates[str(primitive)])
                    for primitive in primitive_counts
                )
                else "not-proven"
            ),
            "draw_local_index_buffer_identity": (
                "observed"
                if ready
                and all(
                    any(item["ready"] for item in candidates[str(primitive)])
                    for primitive in primitive_counts
                )
                else "not-proven"
            ),
            "declaration_bytes": "not-observed",
            "meb_identity": "not-proven",
            "shader_permutation": "not-proven",
            "constant_values": "not-proven",
            "texture_identity": "not-proven",
        },
    }


def validate_file(
    unique_geometry_path: str | Path,
    *,
    primitive_counts: tuple[int, ...] = DEFAULT_PRIMITIVE_COUNTS,
) -> dict[str, Any]:
    value = json.loads(Path(unique_geometry_path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return build_report(value, primitive_counts=primitive_counts)


def _parse_counts(value: str) -> tuple[int, ...]:
    values = tuple(
        sorted({int(part.strip()) for part in value.split(",") if part.strip()})
    )
    if not values:
        raise argparse.ArgumentTypeError(
            "at least one primitive count is required"
        )
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("unique_geometry")
    parser.add_argument("output")
    parser.add_argument(
        "--primitive-counts",
        type=_parse_counts,
        default=DEFAULT_PRIMITIVE_COUNTS,
    )
    args = parser.parse_args(argv)
    report = validate_file(
        args.unique_geometry,
        primitive_counts=args.primitive_counts,
    )
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "ready": report["ready"],
                "blocking_reasons": report["blocking_reasons"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

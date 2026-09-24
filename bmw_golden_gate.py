"""Validate the real BMW M3 golden asset against a render-facing DrawPacket."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWGoldenRenderGate/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _material_ref(submesh: Mapping[str, Any]) -> str:
    material = submesh.get("material") or {}
    ref = material.get("ref")
    return _norm(ref)


def validate_bmw_golden_gate(
    golden: Mapping[str, Any],
    draw_packet: Mapping[str, Any],
    *,
    material_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    golden_meta = golden.get("golden") or {}
    mesh = golden.get("mesh") or {}
    packet_mesh = draw_packet.get("mesh") or {}

    expected_path = _norm(golden_meta.get("resource"))
    observed_path = _norm(packet_mesh.get("resolved", {}).get("path") or packet_mesh.get("ref"))
    if expected_path and observed_path != expected_path:
        reasons.append("mesh:resource-path-mismatch")

    expected_sha = golden_meta.get("resource_sha256")
    observed_sha = (
        packet_mesh.get("resource_sha256")
        or packet_mesh.get("resolved", {}).get("resource_sha256")
    )
    if expected_sha is not None and observed_sha is not None and observed_sha != expected_sha:
        reasons.append("mesh:resource-sha256-mismatch")

    for key in ("vertex_count", "triangle_count"):
        expected = mesh.get(key)
        observed = packet_mesh.get(key)
        if expected is not None and observed is not None and int(expected) != int(observed):
            reasons.append(f"mesh:{key}-mismatch")

    expected_color = (mesh.get("color460_descriptor") or {}).get("words")
    if expected_color != [4, 6, 0]:
        reasons.append("golden:color460-proof-missing")

    submeshes = draw_packet.get("submeshes") or []
    expected_primitives = mesh.get("primitives") or []
    if expected_primitives and len(submeshes) != len(expected_primitives):
        reasons.append("draw:primitive-count-mismatch")
    primitive_mismatches = []
    for index, expected in enumerate(expected_primitives[:len(submeshes)]):
        observed = submeshes[index] or {}
        if int(observed.get("first_index", -1)) != int(expected.get("first_index", -2)):
            primitive_mismatches.append(index)
        if int(observed.get("index_count", -1)) != int(expected.get("index_count", -2)):
            primitive_mismatches.append(index)
        expected_material = _norm(expected.get("material"))
        observed_material = _material_ref(observed)
        if expected_material and observed_material and expected_material != observed_material:
            primitive_mismatches.append(index)
    if primitive_mismatches:
        reasons.append("draw:primitive-definition-mismatch")

    selection_rows: list[dict[str, Any]] = []
    for index, submesh in enumerate(submeshes):
        material = submesh.get("material") or {}
        selection = material.get("shader_selection") or {}
        row = {
            "submesh": index,
            "status": selection.get("status") or selection.get("selection_status", "none"),
            "vertex_pair_selection_status": (
                selection.get("vertex_pair_selection_status")
                or (selection.get("selected_fxo") or {}).get("vertex_pair_selection_status", "none")
            ),
            "linked_shader_pair": bool(selection.get("linked_shader_pair")),
        }
        selection_rows.append(row)
        if row["status"] != "unique":
            reasons.append(f"shader-selection:{index}:{row['status']}")
        if row["vertex_pair_selection_status"] not in ("unique", "none"):
            reasons.append(
                f"shader-pair-selection:{index}:{row['vertex_pair_selection_status']}"
            )
        if not row["linked_shader_pair"]:
            reasons.append(f"shader-glsl:{index}:missing")

    material_status = None
    if material_binding is not None:
        material_status = material_binding.get("selection_status") or material_binding.get("status")
        if material_status != "unique":
            reasons.append(f"material-binding:{material_status}")
        if material_binding.get("linked_shader_error"):
            reasons.append("material-binding:linked-shader-error")

    return {
        "format": FORMAT,
        "status": "match" if not reasons else "mismatch",
        "ready": not reasons,
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "golden": {
            "resource": golden_meta.get("resource"),
            "resource_sha256": expected_sha,
            "vertex_count": mesh.get("vertex_count"),
            "triangle_count": mesh.get("triangle_count"),
        },
        "observed": {
            "resource": packet_mesh.get("resolved", {}).get("path") or packet_mesh.get("ref"),
            "resource_sha256": observed_sha,
            "vertex_count": packet_mesh.get("vertex_count"),
            "triangle_count": packet_mesh.get("triangle_count"),
        },
        "shader_selection": selection_rows,
    }


def validate_files(
    golden_path: str | Path,
    draw_packet_path: str | Path,
    *,
    material_binding_path: str | Path | None = None,
) -> dict[str, Any]:
    golden = json.loads(Path(golden_path).read_text(encoding="utf-8"))
    packet = json.loads(Path(draw_packet_path).read_text(encoding="utf-8"))
    material = (
        json.loads(Path(material_binding_path).read_text(encoding="utf-8"))
        if material_binding_path
        else None
    )
    return validate_bmw_golden_gate(golden, packet, material_binding=material)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a BMW M3 golden render contract")
    ap.add_argument("golden")
    ap.add_argument("draw_packet")
    ap.add_argument("--material-binding")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    report = validate_files(
        args.golden,
        args.draw_packet,
        material_binding_path=args.material_binding,
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Golden gate for one selected BMW M3 material slice."""
from __future__ import annotations

from typing import Any, Mapping

from bmw_m3_paint_asset_contract import validate_bmw_paint_asset

FORMAT = "SHIFT.BMWMaterialSliceGoldenGate/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def validate_bmw_material_slice_golden(
    golden: Mapping[str, Any],
    material_slice: Mapping[str, Any],
    *,
    primitive_index: int | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    golden_meta = golden.get("golden") or {}
    golden_mesh = golden.get("mesh") or {}
    observed_mesh = material_slice.get("mesh") or {}
    selected_index = material_slice.get("primitive_index") if primitive_index is None else primitive_index

    try:
        selected_index = int(selected_index)
    except (TypeError, ValueError):
        reasons.append("slice:primitive-index-invalid")
        selected_index = -1

    asset_contract = validate_bmw_paint_asset(golden)
    reasons.extend(
        f"asset-contract:{reason}"
        for reason in asset_contract.get("blocking_reasons") or []
    )

    expected_resource = _norm(golden_meta.get("resource"))
    observed_resource = _norm(
        (observed_mesh.get("resolved") or {}).get("path")
        or observed_mesh.get("ref")
        or material_slice.get("golden_identity", {}).get("resource")
    )
    if expected_resource and observed_resource != expected_resource:
        reasons.append("slice:resource-path-mismatch")

    expected_sha = str(golden_meta.get("resource_sha256") or "")
    observed_sha = str(
        (observed_mesh.get("resolved") or {}).get("resource_sha256")
        or observed_mesh.get("resource_sha256")
        or material_slice.get("golden_identity", {}).get("resource_sha256")
        or ""
    )
    if expected_sha and observed_sha != expected_sha:
        reasons.append("slice:resource-sha256-mismatch")

    expected_primitives = list(golden_mesh.get("primitives") or [])
    if selected_index < 0 or selected_index >= len(expected_primitives):
        reasons.append("slice:primitive-index-out-of-range")
        expected_primitive = None
    else:
        expected_primitive = expected_primitives[selected_index]

    observed_submeshes = list(
        material_slice.get("render_command", {}).get("submeshes")
        or material_slice.get("static_draw", {}).get("submeshes")
        or material_slice.get("packet", {}).get("submeshes")
        or []
    )
    if len(observed_submeshes) != 1:
        reasons.append("slice:expected-one-submesh")
        observed_submesh = {}
    else:
        observed_submesh = observed_submeshes[0] or {}

    if expected_primitive is not None:
        expected_first = int(expected_primitive.get("first_index", -1))
        expected_count = int(expected_primitive.get("index_count", -1))
        if int(observed_submesh.get("first_index", -2)) != expected_first:
            reasons.append("slice:first-index-mismatch")
        if int(observed_submesh.get("index_count", -2)) != expected_count:
            reasons.append("slice:index-count-mismatch")

        observed_material = _norm(
            material_slice.get("material_ref")
            or observed_submesh.get("material_ref")
            or (observed_submesh.get("material") or {}).get("ref")
        )
        expected_material = _norm(expected_primitive.get("material"))
        if observed_material != expected_material:
            reasons.append("slice:material-ref-mismatch")

    for key in ("vertex_count", "triangle_count"):
        expected = golden_mesh.get(key)
        observed = observed_mesh.get(key) or (material_slice.get("packet", {}).get("mesh") or {}).get(key)
        if expected is not None and observed is not None and int(expected) != int(observed):
            reasons.append(f"slice:{key}-mismatch")

    paint_contract = material_slice.get("paint_contract")
    paint_shader_gate = material_slice.get("paint_shader_gate")
    if not isinstance(paint_contract, Mapping) or paint_contract.get("ready") is not True:
        reasons.append("slice:paint-contract-not-ready")
    if not isinstance(paint_shader_gate, Mapping) or paint_shader_gate.get("ready") is not True:
        reasons.append("slice:paint-shader-gate-not-ready")

    command = material_slice.get("render_command") or {}
    if command.get("format") != "SHIFT.RenderCommand/1":
        reasons.append("slice:render-command-invalid")
    if command.get("ready") is not True:
        reasons.extend(
            "slice:render-command:" + str(reason)
            for reason in command.get("blocking_reasons") or ["not-ready"]
        )

    ready = not reasons
    return {
        "format": FORMAT,
        "status": "match" if ready else "mismatch",
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "primitive_index": selected_index,
        "expected": {
            "resource": golden_meta.get("resource"),
            "resource_sha256": expected_sha,
            "primitive": expected_primitive,
        },
        "observed": {
            "resource": observed_resource,
            "resource_sha256": observed_sha,
            "material_ref": material_slice.get("material_ref"),
        },
        "asset_contract": asset_contract,
    }

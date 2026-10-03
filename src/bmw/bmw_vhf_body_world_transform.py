"""Recover the canonical BMW body RenderCommand world transform from retail VHF.

The existing VHF scene adapter evaluates the retail vehicle hierarchy in a
row-major *column-vector* matrix convention (translation at indices 3/7/11).
The native SVWT ABI is source-backed as row-major D3D *row-vector* convention
(translation at 12/13/14). The two are mathematically equivalent under an exact
transpose.

Selection is fail-closed on the exact canonical BMW body MEB path and SHA from
SHIFT.BMWGoldenAssetManifest/1. This is a resource/VHF bind transform only; it
does not consume BODY physics pose or claim a dynamic vehicle transform.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from bmw_vulkan_bundle import TARGET_MEB
from render_command import validate_render_command
from vhf_scene_preview import build_vhf_scene

FORMAT = "SHIFT.BMWVHFBodyWorldTransform/1"
SOURCE_SET_FORMAT = "SHIFT.BMWMaterialSliceSet/1"
GOLDEN_FORMAT = "SHIFT.BMWGoldenAssetManifest/1"
DEFAULT_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
DEFAULT_BODY_NODE = "BMW_M3_E36_KIT00_BODY_LODA"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _sha_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _load(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    payload = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {value}")
    return payload


def _finite_matrix16(value: Any, label: str) -> list[float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 16
    ):
        raise ValueError(f"{label} must contain exactly 16 numeric values")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{label} contains non-numeric value")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError(f"{label} contains non-finite value")
        result.append(number)
    return result


def _require_column_affine(matrix: Sequence[float]) -> None:
    # VHF hierarchy evaluates column vectors: translation is the fourth column.
    if any(abs(float(matrix[index])) > 1.0e-6 for index in (12, 13, 14)):
        raise ValueError("VHF body matrix is not column-vector affine")
    if abs(float(matrix[15]) - 1.0) > 1.0e-6:
        raise ValueError("VHF body matrix homogeneous component is not one")


def _transpose4(matrix: Sequence[float]) -> list[float]:
    return [
        float(matrix[column * 4 + row])
        for row in range(4)
        for column in range(4)
    ]


def _require_row_affine(matrix: Sequence[float]) -> None:
    # SVWT/D3D row vectors require a [0,0,0,1] final column.
    if any(abs(float(matrix[index])) > 1.0e-6 for index in (3, 7, 11)):
        raise ValueError("converted BMW world matrix is not D3D row-vector affine")
    if abs(float(matrix[15]) - 1.0) > 1.0e-6:
        raise ValueError("converted BMW world matrix homogeneous component is not one")


def build_bmw_vhf_body_world_transform(
    bff_path: str | Path,
    golden_manifest: str | Path | Mapping[str, Any],
    *,
    vhf_resource: str = DEFAULT_VHF,
    body_node: str = DEFAULT_BODY_NODE,
) -> dict[str, Any]:
    """Select the exact VHF body object and convert its world matrix to SVWT form."""
    golden = _load(golden_manifest)
    if golden.get("format") != GOLDEN_FORMAT:
        raise ValueError(f"golden manifest must be {GOLDEN_FORMAT}")
    identity = golden.get("golden") or {}
    expected_path = _norm(identity.get("resource"))
    expected_sha = str(identity.get("resource_sha256") or "").lower()
    if expected_path != _norm(TARGET_MEB):
        raise ValueError("golden manifest does not identify canonical BMW body MEB")
    if len(expected_sha) != 64:
        raise ValueError("golden BMW body MEB SHA-256 is missing")

    scene = build_vhf_scene(
        bff_path,
        vhf_resource,
        kit="00",
        lod="A",
        include_generic=False,
        include_lightglows=False,
    )
    parts = [row for row in scene.get("parts") or [] if isinstance(row, Mapping)]
    matches = [
        row
        for row in parts
        if str(row.get("name") or "").casefold() == body_node.casefold()
        and _norm(row.get("resource")) == expected_path
        and str(row.get("resource_sha256") or "").lower() == expected_sha
    ]
    if len(matches) != 1:
        raise ValueError(
            "expected exactly one canonical BMW VHF body object by name/path/SHA; "
            f"found {len(matches)}"
        )

    part = matches[0]
    vhf_matrix = _finite_matrix16(part.get("world_matrix"), "VHF body world matrix")
    _require_column_affine(vhf_matrix)
    d3d_matrix = _transpose4(vhf_matrix)
    _require_row_affine(d3d_matrix)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "source": {
            "archive": Path(bff_path).name,
            "vhf_resource": vhf_resource,
            "scene_format": scene.get("format"),
            "node_name": part.get("name"),
            "matrix_number": part.get("matrix_number"),
            "mesh_resource": part.get("resource"),
            "mesh_sha256": part.get("resource_sha256"),
            "golden_resource": identity.get("resource"),
            "golden_resource_sha256": identity.get("resource_sha256"),
        },
        "vhf_world_matrix": vhf_matrix,
        "world_matrix": d3d_matrix,
        "world_matrix_sha256": _sha_json(d3d_matrix),
        "translation_xyz": [d3d_matrix[12], d3d_matrix[13], d3d_matrix[14]],
        "convention": {
            "source": "VHF row-major column-vector hierarchy",
            "target": "SVWT row-major D3D row-vector",
            "operation": "exact 4x4 transpose",
        },
        "boundary": {
            "canonical_body_meb_identity_proven": True,
            "vhf_object_transform_proven": True,
            "body_physics_pose_consumed": False,
            "phase700_runtime_pose_handoff_consumed": False,
            "dynamic_vehicle_world_transform_claimed": False,
            "body_local_to_meb_object_bind_proven": False,
        },
    }


def apply_bmw_vhf_body_world_transform(
    material_slice_set: str | Path | Mapping[str, Any],
    transform: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the same BMW material-set ABI with its proven VHF world matrix attached."""
    payload = _load(material_slice_set)
    if payload.get("format") != SOURCE_SET_FORMAT:
        raise ValueError(f"material slice set must be {SOURCE_SET_FORMAT}")
    if payload.get("ready") is not True:
        raise ValueError("BMW material slice set is not ready")
    if transform.get("format") != FORMAT or transform.get("ready") is not True:
        raise ValueError(f"transform must be a ready {FORMAT}")

    mesh_identity = payload.get("mesh_identity") or {}
    source = transform.get("source") or {}
    if _norm(mesh_identity.get("resource")) != _norm(TARGET_MEB):
        raise ValueError("BMW material set does not identify canonical body MEB")
    if _norm(source.get("mesh_resource")) != _norm(mesh_identity.get("resource")):
        raise ValueError("VHF transform MEB path disagrees with material set")
    if str(source.get("mesh_sha256") or "").lower() != str(
        mesh_identity.get("resource_sha256") or ""
    ).lower():
        raise ValueError("VHF transform MEB SHA-256 disagrees with material set")

    matrix = _finite_matrix16(transform.get("world_matrix"), "D3D BMW world matrix")
    _require_row_affine(matrix)
    raw_command = payload.get("render_command")
    if not isinstance(raw_command, Mapping):
        raise ValueError("BMW material set has no RenderCommand")
    command = deepcopy(dict(raw_command))
    existing = command.get("world_matrix")
    if existing is not None:
        existing_matrix = _finite_matrix16(existing, "existing BMW world matrix")
        if existing_matrix != matrix:
            raise ValueError("existing BMW world matrix conflicts with proven VHF transform")
    command["world_matrix"] = matrix
    validation = validate_render_command(command)
    blockers = [str(reason) for reason in validation.get("blocking_reasons") or []]
    if validation.get("valid") is not True or blockers:
        raise ValueError(
            "VHF-transformed BMW RenderCommand failed validation: "
            + ",".join(blockers or ["invalid"])
        )

    result = deepcopy(payload)
    # Preserve the established Phase 529 ABI: world_matrix is already a legal
    # RenderCommand field and Phase 529 accepts/equality-checks non-null matrices.
    result["render_command"] = command
    result["vhf_body_world_transform"] = deepcopy(dict(transform))
    result["source_material_slice_set"] = {
        "format": SOURCE_SET_FORMAT,
        "identity_sha256": payload.get("identity_sha256"),
        "world_matrix_was_null": existing is None,
    }
    result["world_matrix_sha256"] = _sha_json(matrix)
    result["boundary"] = {
        "material_slice_set_abi_preserved": True,
        "render_command_world_matrix_from_vhf": True,
        "canonical_body_meb_identity_revalidated": True,
        "phase700_runtime_pose_handoff_consumed": False,
        "dynamic_vehicle_world_transform_claimed": False,
        "body_local_to_meb_object_bind_proven": False,
    }
    return result

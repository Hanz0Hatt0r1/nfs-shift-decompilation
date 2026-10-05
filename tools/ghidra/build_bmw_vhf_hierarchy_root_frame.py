#!/usr/bin/env python3
"""Prove the exact canonical BMW VHF HIERARCHY-root resource frame.

The positive ``SHIFT.BMWVehicleRenderModelResourceJoin/1`` proves which retail
VHF resource belongs to the BMW vehicle RenderHierarchy, but intentionally does
not claim any relation between that VHF root and the dynamic outer Vehicle
frame.  This pass makes the resource-side target of that later join exact: the
unique direct HIERARCHY node, its MatrixNumber, the exact MATRIX parent chain,
and the resolved affine matrix under the same parent*local convention used by
the VHF scene evaluator.

It is deliberately fail-closed.  Resource identity and matrix identity are not
promoted to outer-Vehicle frame identity.  No callgraph, visual or equal-value
heuristic participates in this proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shift_importer import BFF  # noqa: E402

FORMAT = "SHIFT.BMWVHFHierarchyRootFrame/1"
RESOURCE_JOIN_FORMAT = "SHIFT.BMWVehicleRenderModelResourceJoin/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
VEHICLE_NAME = "BMW_M3_E36"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
EXPECTED_ROOT_NODE_NAME = "Root"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_float_list(raw: str | None, count: int, label: str) -> list[float]:
    values = str(raw or "").split()
    if len(values) != count:
        raise ValueError(f"{label} must contain exactly {count} floats")
    result: list[float] = []
    for value in values:
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError(f"{label} contains non-numeric value {value!r}") from exc
        if not math.isfinite(number):
            raise ValueError(f"{label} contains non-finite value")
        result.append(number)
    return result


def _quat_matrix(q: Sequence[float]) -> list[float]:
    if len(q) != 4:
        raise ValueError("quaternion must contain four values")
    x, y, z, w = (float(value) for value in q)
    return [
        1 - 2 * (y * y + z * z),
        2 * (x * y - z * w),
        2 * (x * z + y * w),
        0.0,
        2 * (x * y + z * w),
        1 - 2 * (x * x + z * z),
        2 * (y * z - x * w),
        0.0,
        2 * (x * z - y * w),
        2 * (y * z + x * w),
        1 - 2 * (x * x + y * y),
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    ]


def _matrix_from_attrs(attrs: Mapping[str, str]) -> tuple[list[float], list[float], list[float]]:
    offset = _finite_float_list(attrs.get("Offset"), 3, "MATRIX Offset")
    orientation = _finite_float_list(attrs.get("Orientation"), 4, "MATRIX Orientation")
    matrix = _quat_matrix(orientation)
    matrix[3], matrix[7], matrix[11] = offset
    return matrix, offset, orientation


def _mat_mul(a: Sequence[float], b: Sequence[float]) -> list[float]:
    if len(a) != 16 or len(b) != 16:
        raise ValueError("matrix multiply requires 4x4 matrices")
    return [
        sum(float(a[row * 4 + k]) * float(b[k * 4 + col]) for k in range(4))
        for row in range(4)
        for col in range(4)
    ]


def _transpose4(matrix: Sequence[float]) -> list[float]:
    if len(matrix) != 16:
        raise ValueError("matrix transpose requires 4x4 matrix")
    return [
        float(matrix[col * 4 + row])
        for row in range(4)
        for col in range(4)
    ]


def _matrix_is_identity(matrix: Sequence[float], tolerance: float = 1.0e-9) -> bool:
    identity = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    return all(abs(float(a) - b) <= tolerance for a, b in zip(matrix, identity))


def _validate_resource_join(join: Mapping[str, Any]) -> dict[str, Any]:
    if join.get("format") != RESOURCE_JOIN_FORMAT or join.get("ready") is not True:
        raise ValueError("BMW Vehicle Render Model resource join is not positive")

    retail = join.get("retail")
    if isinstance(retail, Mapping):
        if retail.get("program") != PROGRAM or retail.get("md5") != PE_MD5:
            raise ValueError("resource join retail executable identity drift")

    handoff = join.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("resource join handoff missing")
    if handoff.get("vehicle_render_hierarchy_owner_ready") is not True:
        raise ValueError("vehicle RenderHierarchy owner gate is not ready")
    if handoff.get("selected_BMW_vehicle_render_model_value_ready") is not True:
        raise ValueError("selected BMW Vehicle Render Model gate is not ready")
    if handoff.get("canonical_BMW_VHF_resource_join_ready") is not True:
        raise ValueError("canonical BMW VHF resource gate is not ready")
    if handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise ValueError("resource join unexpectedly preclaims outer/VHF frame identity")
    if handoff.get("BODY0_bind_frame_proof_ready") is not False:
        raise ValueError("resource join unexpectedly preclaims BODY0 bind-frame proof")

    resource = join.get("canonical_bmw_vhf_resource")
    if not isinstance(resource, Mapping):
        raise ValueError("canonical BMW VHF resource identity missing")
    if _norm(resource.get("resolved_path")) != _norm(CANONICAL_VHF):
        raise ValueError("canonical BMW VHF logical path drift")
    if resource.get("root_tag") != "CAR" or resource.get("root_name") != VEHICLE_NAME:
        raise ValueError("canonical BMW VHF CAR identity drift")
    if resource.get("root_node_type") != "HIERARCHY":
        raise ValueError("canonical BMW VHF hierarchy-root type drift")
    if resource.get("canonical_BMW_VHF_resource_join_ready") is not True:
        raise ValueError("canonical BMW VHF resource row is not ready")
    decoded_sha = str(resource.get("decoded_sha256") or "").lower()
    if len(decoded_sha) != 64:
        raise ValueError("canonical BMW VHF decoded SHA-256 missing")
    archive_sha = str(resource.get("archive_sha256") or "").lower()
    if archive_sha and len(archive_sha) != 64:
        raise ValueError("canonical BMW VHF archive SHA-256 invalid")
    return dict(resource)


def _matrix_table(root: ET.Element) -> dict[str, dict[str, str]]:
    table: dict[str, dict[str, str]] = {}
    for matrix in root.iter("MATRIX"):
        matrix_id = matrix.get("id")
        if matrix_id is None:
            raise ValueError("VHF MATRIX without id")
        key = str(matrix_id)
        if key in table:
            raise ValueError(f"duplicate VHF MATRIX id {key!r}")
        attrs = dict(matrix.attrib)
        # Fail closed instead of inheriting the preview adapter's permissive
        # default values.  A positive frame proof must be fully source-backed.
        _finite_float_list(attrs.get("Offset"), 3, f"MATRIX {key} Offset")
        _finite_float_list(attrs.get("Orientation"), 4, f"MATRIX {key} Orientation")
        table[key] = attrs
    return table


def _resolve_matrix_chain(
    matrix_id: str,
    matrices: Mapping[str, Mapping[str, str]],
) -> tuple[list[float], list[dict[str, Any]]]:
    active: set[str] = set()
    cache: dict[str, list[float]] = {}
    chain_cache: dict[str, list[dict[str, Any]]] = {}

    def visit(key: str) -> tuple[list[float], list[dict[str, Any]]]:
        if key in cache:
            return list(cache[key]), [dict(row) for row in chain_cache[key]]
        if key in active:
            raise ValueError(f"VHF MATRIX parent cycle at id {key!r}")
        attrs = matrices.get(key)
        if attrs is None:
            raise ValueError(f"VHF hierarchy root references missing MATRIX id {key!r}")
        active.add(key)
        local, offset, orientation = _matrix_from_attrs(attrs)
        parent_raw = attrs.get("parent")
        parent = str(parent_raw) if parent_raw not in (None, "") else None
        row = {
            "matrix_id": key,
            "parent": parent,
            "offset_xyz": offset,
            "orientation_xyzw": orientation,
            "local_matrix_column_vector": local,
        }
        if parent is None:
            world = local
            chain = [row]
        else:
            parent_world, parent_chain = visit(parent)
            world = _mat_mul(parent_world, local)
            chain = parent_chain + [row]
        active.remove(key)
        cache[key] = list(world)
        chain_cache[key] = [dict(item) for item in chain]
        return list(world), [dict(item) for item in chain]

    return visit(str(matrix_id))


def analyze_decoded_vhf(
    resource_join: Mapping[str, Any],
    decoded_vhf: bytes,
    *,
    source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resource = _validate_resource_join(resource_join)
    decoded_sha = _sha256_bytes(decoded_vhf)
    expected_sha = str(resource["decoded_sha256"]).lower()
    if decoded_sha != expected_sha:
        raise ValueError("decoded BMW VHF SHA-256 disagrees with positive resource join")

    try:
        root = ET.fromstring(decoded_vhf)
    except ET.ParseError as exc:
        raise ValueError(f"canonical BMW VHF XML parse failed: {exc}") from exc
    if root.tag != "CAR" or root.get("Name") != VEHICLE_NAME:
        raise ValueError("canonical BMW VHF decoded CAR identity drift")

    hierarchy_nodes = [
        node
        for node in root.findall("NODE")
        if str(node.get("type") or "").upper() == "HIERARCHY"
    ]
    if len(hierarchy_nodes) != 1:
        raise ValueError(
            "expected exactly one direct canonical BMW VHF HIERARCHY root; "
            f"found {len(hierarchy_nodes)}"
        )
    hierarchy = hierarchy_nodes[0]
    node_name = str(hierarchy.get("Name") or "")
    if node_name != EXPECTED_ROOT_NODE_NAME:
        raise ValueError(
            f"canonical BMW VHF HIERARCHY root name drift: {node_name!r}"
        )
    matrix_number = hierarchy.get("MatrixNumber")
    if matrix_number is None or not str(matrix_number):
        raise ValueError("canonical BMW VHF HIERARCHY root has no MatrixNumber")

    matrices = _matrix_table(root)
    world_column, chain = _resolve_matrix_chain(str(matrix_number), matrices)
    local_attrs = matrices[str(matrix_number)]
    local_column, offset, orientation = _matrix_from_attrs(local_attrs)
    world_row = _transpose4(world_column)
    local_row = _transpose4(local_column)

    source_record = dict(source or {})
    source_record.update(
        {
            "resource_join_format": RESOURCE_JOIN_FORMAT,
            "resolved_path": resource.get("resolved_path"),
            "archive": resource.get("archive"),
            "archive_sha256": resource.get("archive_sha256"),
            "entry_index": resource.get("entry_index"),
            "decoded_sha256": decoded_sha,
            "decoded_size": len(decoded_vhf),
        }
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "canonical-bmw-vhf-hierarchy-root-frame-proven",
        "ready": True,
        "BLOCKER": (
            "SHIFT.BMWBody0BindFrameProof/1: outer Vehicle-root -> exact BMW VHF "
            "vehicle-root relation"
        ),
        "INPUT": {
            "resource_join": RESOURCE_JOIN_FORMAT,
            "canonical_vhf": CANONICAL_VHF,
        },
        "OUTPUT": (
            "exact canonical BMW VHF HIERARCHY Root node, MatrixNumber, source "
            "parent chain, and resolved affine matrices"
        ),
        "CONSUMER": (
            "SHIFT.OuterVehicleRenderRootDeltaProvenance/1 value roots -> exact "
            "outer Vehicle/VHF identity-or-fixed-affine join"
        ),
        "source": source_record,
        "vehicle_root_frame": {
            "car_tag": root.tag,
            "car_name": root.get("Name"),
            "node_type": hierarchy.get("type"),
            "node_name": node_name,
            "node_path": f"CAR[{VEHICLE_NAME}]/NODE[HIERARCHY:{node_name}]",
            "matrix_number": str(matrix_number),
            "matrix_record_present": True,
            "matrix_parent_chain": chain,
            "matrix_parent_chain_ids": [row["matrix_id"] for row in chain],
            "local_offset_xyz": offset,
            "local_orientation_xyzw": orientation,
            "local_matrix_column_vector": local_column,
            "local_matrix_row_vector": local_row,
            "world_matrix_column_vector": world_column,
            "world_matrix_row_vector": world_row,
            "local_matrix_is_identity": _matrix_is_identity(local_column),
            "world_matrix_is_identity": _matrix_is_identity(world_column),
            "convention": {
                "source": "VHF row-major column-vector hierarchy",
                "composition": "world = parent_world * local",
                "row_vector_conversion": "exact 4x4 transpose",
            },
        },
        "provenance": {
            "vehicle_render_hierarchy_resource_owner_join_ready": True,
            "canonical_BMW_VHF_resource_identity_revalidated": True,
            "decoded_payload_sha256_matches_resource_join": True,
            "unique_direct_HIERARCHY_root_ready": True,
            "exact_root_node_name_ready": True,
            "exact_root_MatrixNumber_ready": True,
            "exact_root_MATRIX_record_ready": True,
            "exact_root_parent_chain_ready": True,
            "exact_root_affine_matrix_ready": True,
        },
        "handoff": {
            "canonical_BMW_VHF_hierarchy_root_frame_ready": True,
            "canonical_BMW_VHF_hierarchy_root_matrix_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "next_frontier": (
                "join only source-backed FUN_00795d60 delta value roots to this exact "
                "BMW VHF HIERARCHY Root frame; prove identity or exact fixed affine delta"
            ),
        },
        "limits": {
            "resource_identity_is_frame_identity": False,
            "root_identity_matrix_implies_outer_vehicle_identity": False,
            "equal_numeric_values_are_provenance": False,
            "callgraph_adjacency_is_ownership": False,
            "visual_similarity_is_frame_identity": False,
            "dynamic_outer_vehicle_pose_consumed": False,
            "BODY0_bind_frame_claimed": False,
            "runtime_capture_required": False,
            "original_game_executed": False,
        },
    }


def analyze_archive(
    resource_join: Mapping[str, Any],
    primary_vehicle_archive: Path,
) -> dict[str, Any]:
    resource = _validate_resource_join(resource_join)
    expected_archive = str(resource.get("archive") or "")
    if primary_vehicle_archive.name != expected_archive:
        raise ValueError("primary BMW archive name disagrees with positive resource join")
    expected_archive_sha = str(resource.get("archive_sha256") or "").lower()
    if expected_archive_sha and _sha256_file(primary_vehicle_archive) != expected_archive_sha:
        raise ValueError("primary BMW archive SHA-256 disagrees with positive resource join")

    with BFF(primary_vehicle_archive) as archive:
        hits = [
            entry
            for entry in archive.entries
            if _norm(entry.path) == _norm(resource.get("resolved_path"))
        ]
        if len(hits) != 1:
            raise ValueError(
                "expected exactly one canonical BMW VHF entry in primary archive; "
                f"found {len(hits)}"
            )
        entry = hits[0]
        expected_index = resource.get("entry_index")
        if isinstance(expected_index, int) and int(entry.index) != expected_index:
            raise ValueError("canonical BMW VHF archive entry index drift")
        decoded = archive.extract_entry(entry, type2="lzx")

    return analyze_decoded_vhf(
        resource_join,
        decoded,
        source={
            "archive_path": str(primary_vehicle_archive),
            "archive_sha256_verified": bool(expected_archive_sha),
            "entry_index_verified": isinstance(resource.get("entry_index"), int),
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resource_join", type=Path)
    parser.add_argument("primary_vehicle_archive", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze_archive(_load_json(args.resource_join), args.primary_vehicle_archive)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

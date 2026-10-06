"""Consume the positive BMW VHF root-frame handoff in the production scene path.

This module does not rediscover or semantically adjudicate the BMW VHF root.
Process 1 owns that proof in ``SHIFT.BMWVHFHierarchyRootFrame/1``.  Process 3
reopens the exact admitted VHF payload only to verify that the production scene
parser uses the same explicit MATRIX chain/convention, that the canonical BMW
body OBJECT is descended from that root frame, and that the resulting static
object matrix survives into every emitted Vulkan SVWT packet.

The static VHF frame remains resource/bootstrap state.  It is never promoted to
the dynamic vehicle pose; live motion remains the freshness-gated Process 2 ->
Process 3 path.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any, Mapping, Sequence
import xml.etree.ElementTree as ET

from shift_importer import BFF

FORMAT = "SHIFT.BMWVHFRootFrameSceneConsumer/1"
ROOT_FRAME_FORMAT = "SHIFT.BMWVHFHierarchyRootFrame/1"
VHF_TRANSFORM_FORMAT = "SHIFT.BMWVHFBodyWorldTransform/1"
SCENE_SET_FORMAT = "SHIFT.NativeSceneVulkanSet/1"
SVWT_FORMAT = "SHIFT.VulkanWorldTransformPacket/1"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
VEHICLE_NAME = "BMW_M3_E36"
ROOT_NODE_NAME = "Root"
SVWT_HEADER = struct.Struct("<4sIII")
SVWT_MATRIX = struct.Struct("<16f")


def _load(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    payload = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {value}")
    return payload


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_matrix16(value: Any, label: str) -> list[float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
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
    x, y, z, w = (float(value) for value in q)
    return [
        1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0.0,
        2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0.0,
        2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _matrix_from_attrs(attrs: Mapping[str, str], *, matrix_id: str) -> list[float]:
    offset = _finite_float_list(attrs.get("Offset"), 3, f"MATRIX {matrix_id} Offset")
    orientation = _finite_float_list(
        attrs.get("Orientation"), 4, f"MATRIX {matrix_id} Orientation"
    )
    matrix = _quat_matrix(orientation)
    matrix[3], matrix[7], matrix[11] = offset
    return matrix


def _mat_mul(a: Sequence[float], b: Sequence[float]) -> list[float]:
    return [
        sum(float(a[row * 4 + k]) * float(b[k * 4 + col]) for k in range(4))
        for row in range(4)
        for col in range(4)
    ]


def _transpose4(matrix: Sequence[float]) -> list[float]:
    return [float(matrix[col * 4 + row]) for row in range(4) for col in range(4)]


def _matrix_table(root: ET.Element) -> dict[str, dict[str, str]]:
    table: dict[str, dict[str, str]] = {}
    for matrix in root.iter("MATRIX"):
        matrix_id = matrix.get("id")
        if matrix_id is None:
            raise ValueError("VHF MATRIX without id")
        key = str(matrix_id)
        if key in table:
            raise ValueError(f"duplicate VHF MATRIX id {key!r}")
        table[key] = dict(matrix.attrib)
    return table


def _resolve_matrix_chain(
    matrix_id: str,
    matrices: Mapping[str, Mapping[str, str]],
) -> tuple[list[float], list[str]]:
    active: set[str] = set()
    cache: dict[str, tuple[list[float], list[str]]] = {}

    def visit(key: str) -> tuple[list[float], list[str]]:
        if key in cache:
            world, chain = cache[key]
            return list(world), list(chain)
        if key in active:
            raise ValueError(f"VHF MATRIX parent cycle at id {key!r}")
        attrs = matrices.get(key)
        if attrs is None:
            raise ValueError(f"scene path references missing VHF MATRIX id {key!r}")
        active.add(key)
        local = _matrix_from_attrs(attrs, matrix_id=key)
        parent_raw = attrs.get("parent")
        parent = str(parent_raw) if parent_raw not in (None, "") else None
        if parent is None:
            world, chain = local, [key]
        else:
            parent_world, parent_chain = visit(parent)
            world, chain = _mat_mul(parent_world, local), [*parent_chain, key]
        active.remove(key)
        cache[key] = (list(world), list(chain))
        return list(world), list(chain)

    return visit(str(matrix_id))


def _validate_root_handoff(root_handoff: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if root_handoff.get("format") != ROOT_FRAME_FORMAT or root_handoff.get("ready") is not True:
        raise ValueError(f"root-frame handoff must be a ready {ROOT_FRAME_FORMAT}")
    handoff = root_handoff.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("root-frame handoff gates missing")
    for gate in (
        "canonical_BMW_VHF_hierarchy_root_frame_ready",
        "canonical_BMW_VHF_hierarchy_root_matrix_ready",
    ):
        if handoff.get(gate) is not True:
            raise ValueError(f"root-frame handoff gate not ready: {gate}")
    for gate in (
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "outer_vehicle_root_to_VHF_fixed_affine_delta_ready",
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
    ):
        if handoff.get(gate) is not False:
            raise ValueError(f"root-frame handoff unexpectedly preclaims semantic gate: {gate}")
    source = root_handoff.get("source")
    frame = root_handoff.get("vehicle_root_frame")
    if not isinstance(source, Mapping) or not isinstance(frame, Mapping):
        raise ValueError("root-frame source/frame payload missing")
    if _norm(source.get("resolved_path")) != _norm(CANONICAL_VHF):
        raise ValueError("root-frame canonical VHF path drift")
    if frame.get("node_type") != "HIERARCHY" or frame.get("node_name") != ROOT_NODE_NAME:
        raise ValueError("root-frame HIERARCHY Root identity drift")
    return dict(source), dict(frame)


def _exact_vhf_payload(
    bff_path: str | Path,
    vhf_resource: str,
) -> tuple[dict[str, Any], bytes]:
    archive_path = Path(bff_path).resolve()
    if _norm(vhf_resource) != _norm(CANONICAL_VHF):
        raise ValueError("scene consumer requires the canonical primary BMW VHF path")
    with BFF(archive_path) as bff:
        hits = [entry for entry in bff.entries if _norm(entry.path) == _norm(vhf_resource)]
        if len(hits) != 1:
            raise ValueError(
                "expected exactly one canonical primary BMW VHF entry by exact path; "
                f"found {len(hits)}"
            )
        entry = hits[0]
        decoded = bff.extract_entry(entry, type2="lzx")
    return {
        "archive": archive_path.name,
        "archive_sha256": _sha256_file(archive_path),
        "entry_index": int(entry.index),
        "path": entry.path,
        "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
        "decoded_size": len(decoded),
    }, decoded


def _require_same_source(
    observed: Mapping[str, Any],
    root_source: Mapping[str, Any],
    transform_source: Mapping[str, Any],
) -> None:
    transform_entry = transform_source.get("vhf_entry")
    if not isinstance(transform_entry, Mapping):
        raise ValueError("Phase 645 VHF source identity missing")
    comparisons = (
        ("archive", observed.get("archive"), root_source.get("archive")),
        ("archive_sha256", observed.get("archive_sha256"), root_source.get("archive_sha256")),
        ("entry_index", observed.get("entry_index"), root_source.get("entry_index")),
        ("path", _norm(observed.get("path")), _norm(root_source.get("resolved_path"))),
        ("decoded_sha256", observed.get("decoded_sha256"), root_source.get("decoded_sha256")),
        ("decoded_size", observed.get("decoded_size"), root_source.get("decoded_size")),
        ("transform archive", observed.get("archive"), transform_entry.get("archive")),
        ("transform archive_sha256", observed.get("archive_sha256"), transform_entry.get("archive_sha256")),
        ("transform entry_index", observed.get("entry_index"), transform_entry.get("entry_index")),
        ("transform path", _norm(observed.get("path")), _norm(transform_entry.get("path"))),
        ("transform decoded_sha256", observed.get("decoded_sha256"), transform_entry.get("decoded_sha256")),
        ("transform decoded_size", observed.get("decoded_size"), transform_entry.get("decoded_size")),
    )
    for label, left, right in comparisons:
        if left != right:
            raise ValueError(f"root-frame scene consumer source mismatch: {label}")


def build_bmw_vhf_root_frame_scene_consumer(
    bff_path: str | Path,
    root_frame_handoff: str | Path | Mapping[str, Any],
    vhf_transform: str | Path | Mapping[str, Any],
) -> dict[str, Any]:
    """Validate Root -> canonical BODY OBJECT transport before Vulkan composition."""
    root_handoff = _load(root_frame_handoff)
    root_source, root_frame = _validate_root_handoff(root_handoff)
    transform = _load(vhf_transform)
    if transform.get("format") != VHF_TRANSFORM_FORMAT or transform.get("ready") is not True:
        raise ValueError(f"VHF transform must be a ready {VHF_TRANSFORM_FORMAT}")
    transform_source = transform.get("source")
    if not isinstance(transform_source, Mapping):
        raise ValueError("Phase 645 VHF transform source missing")
    vhf_resource = str(transform_source.get("vhf_resource") or "")
    observed, decoded = _exact_vhf_payload(bff_path, vhf_resource)
    _require_same_source(observed, root_source, transform_source)

    try:
        root = ET.fromstring(decoded)
    except ET.ParseError as exc:
        raise ValueError(f"canonical BMW VHF XML parse failed: {exc}") from exc
    if root.tag != "CAR" or root.get("Name") != VEHICLE_NAME:
        raise ValueError("canonical BMW VHF CAR identity drift")
    matrices = _matrix_table(root)

    hierarchy_nodes = [
        node for node in root.findall("NODE")
        if str(node.get("type") or "").upper() == "HIERARCHY"
    ]
    if len(hierarchy_nodes) != 1:
        raise ValueError(
            "scene consumer requires exactly one direct VHF HIERARCHY root; "
            f"found {len(hierarchy_nodes)}"
        )
    hierarchy = hierarchy_nodes[0]
    if hierarchy.get("Name") != ROOT_NODE_NAME:
        raise ValueError("scene consumer VHF HIERARCHY root name drift")
    root_matrix_number = str(hierarchy.get("MatrixNumber") or "")
    if not root_matrix_number:
        raise ValueError("scene consumer VHF HIERARCHY Root has no MatrixNumber")
    root_world_column, root_chain = _resolve_matrix_chain(root_matrix_number, matrices)
    root_world_row = _transpose4(root_world_column)

    if root_matrix_number != str(root_frame.get("matrix_number") or ""):
        raise ValueError("scene parser Root MatrixNumber disagrees with Process 1 handoff")
    if root_chain != [str(value) for value in root_frame.get("matrix_parent_chain_ids") or []]:
        raise ValueError("scene parser Root MATRIX parent chain disagrees with Process 1 handoff")
    if root_world_column != _finite_matrix16(
        root_frame.get("world_matrix_column_vector"),
        "Process 1 root world column matrix",
    ):
        raise ValueError("scene parser Root world matrix disagrees with Process 1 handoff")
    if root_world_row != _finite_matrix16(
        root_frame.get("world_matrix_row_vector"),
        "Process 1 root world row matrix",
    ):
        raise ValueError("scene parser Root row-vector transpose disagrees with Process 1 handoff")

    body_name = str(transform_source.get("node_name") or "")
    mesh_resource = _norm(transform_source.get("mesh_resource"))
    body_nodes = []
    for node in root.iter("NODE"):
        if str(node.get("type") or "").upper() != "OBJECT":
            continue
        if str(node.get("Name") or "") != body_name:
            continue
        resource = node.find("RESOURCE")
        if resource is None or _norm(resource.get("Filename")) != mesh_resource:
            continue
        body_nodes.append(node)
    if len(body_nodes) != 1:
        raise ValueError(
            "scene consumer expected exactly one canonical Phase 645 BMW BODY OBJECT; "
            f"found {len(body_nodes)}"
        )
    body = body_nodes[0]
    body_matrix_number = str(body.get("MatrixNumber") or "")
    if not body_matrix_number:
        raise ValueError("canonical BMW BODY OBJECT has no MatrixNumber")
    body_world_column, body_chain = _resolve_matrix_chain(body_matrix_number, matrices)
    if root_matrix_number not in body_chain:
        raise ValueError("canonical BMW BODY OBJECT MATRIX chain does not descend from HIERARCHY Root")
    body_world_row = _transpose4(body_world_column)
    if body_world_column != _finite_matrix16(
        transform.get("vhf_world_matrix"),
        "Phase 645 VHF body world matrix",
    ):
        raise ValueError("strict BODY OBJECT matrix disagrees with Phase 645 VHF matrix")
    if body_world_row != _finite_matrix16(
        transform.get("world_matrix"),
        "Phase 645 D3D body world matrix",
    ):
        raise ValueError("strict BODY OBJECT transpose disagrees with Phase 645 D3D matrix")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "parser-bootstrap-ready",
        "ready": False,
        "parser_bootstrap_ready": True,
        "vulkan_object_frame_ready": False,
        "blocking_reasons": ["root-frame-scene-consumer:vulkan-object-frame-not-checked"],
        "BLOCKER": "production BMW scene path must preserve the positive canonical VHF Root frame through Vulkan object-frame construction",
        "INPUT": {
            "root_frame": ROOT_FRAME_FORMAT,
            "vhf_transform": VHF_TRANSFORM_FORMAT,
            "canonical_vhf": CANONICAL_VHF,
        },
        "OUTPUT": "strict parser/bootstrap Root ancestry and matching canonical BODY object transform; Vulkan packet pending",
        "CONSUMER": "Phase 643 BMW vehicle draw construction and native Vulkan SVWT object frame",
        "source": observed,
        "root_frame": {
            "node_name": ROOT_NODE_NAME,
            "matrix_number": root_matrix_number,
            "matrix_parent_chain_ids": root_chain,
            "world_matrix_column_vector": root_world_column,
            "world_matrix_row_vector": root_world_row,
        },
        "body_object_frame": {
            "node_name": body_name,
            "mesh_resource": transform_source.get("mesh_resource"),
            "matrix_number": body_matrix_number,
            "matrix_parent_chain_ids": body_chain,
            "root_matrix_number_is_ancestor": True,
            "world_matrix_column_vector": body_world_column,
            "world_matrix_row_vector": body_world_row,
        },
        "convention": {
            "vhf_storage": "row-major",
            "vhf_vector": "column-vector",
            "vhf_composition": "world = parent_world * local",
            "scene_to_d3d": "exact 4x4 transpose",
            "d3d_storage": "row-major",
            "d3d_vector": "row-vector",
        },
        "boundary": {
            "process1_root_frame_consumed": True,
            "process1_root_frame_reproved_by_process3": False,
            "explicit_MATRIX_records_required": True,
            "missing_MATRIX_identity_fallback_allowed": False,
            "primary_vhf_exact_path_required": True,
            "basename_fallback_allowed": False,
            "cockpit_vhf_substitution_allowed": False,
            "static_vhf_frame_is_dynamic_vehicle_pose": False,
            "outer_vehicle_vhf_semantic_relation_claimed": False,
            "physics_motion_claimed": False,
        },
    }


def _f32_matrix(matrix: Sequence[float]) -> list[float]:
    return list(SVWT_MATRIX.unpack(SVWT_MATRIX.pack(*[float(value) for value in matrix])))


def _read_svwt(path: Path) -> list[float]:
    data = path.read_bytes()
    expected_size = SVWT_HEADER.size + SVWT_MATRIX.size
    if len(data) != expected_size:
        raise ValueError(f"SVWT byte size mismatch: {len(data)} != {expected_size}")
    magic, version, convention, matrix_bytes = SVWT_HEADER.unpack_from(data, 0)
    if magic != b"SVWT" or version != 1 or convention != 1 or matrix_bytes != SVWT_MATRIX.size:
        raise ValueError("SVWT header/convention drift")
    return list(SVWT_MATRIX.unpack_from(data, SVWT_HEADER.size))


def finalize_bmw_vhf_root_frame_scene_consumer(
    consumer: Mapping[str, Any],
    scene_set_dir: str | Path,
) -> dict[str, Any]:
    """Require every production BMW vehicle draw to carry the same SVWT frame."""
    if consumer.get("format") != FORMAT or consumer.get("parser_bootstrap_ready") is not True:
        raise ValueError(f"consumer must have a ready parser/bootstrap {FORMAT} stage")
    scene_root = Path(scene_set_dir).resolve()
    manifest_path = scene_root / "bundle_set_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("format") != SCENE_SET_FORMAT:
        raise ValueError(f"scene set must be {SCENE_SET_FORMAT}")
    if manifest.get("ready") is not True:
        raise ValueError("scene set is not ready")

    expected = _f32_matrix(
        _finite_matrix16(
            (consumer.get("body_object_frame") or {}).get("world_matrix_row_vector"),
            "consumer BODY object D3D matrix",
        )
    )
    vehicle_rows = [
        row for row in manifest.get("draws") or []
        if isinstance(row, Mapping) and row.get("source_group") == "vehicle"
    ]
    if not vehicle_rows:
        raise ValueError("scene set has no vehicle draws")

    packets: list[dict[str, Any]] = []
    for row in vehicle_rows:
        bundle = row.get("bundle")
        if not isinstance(bundle, Mapping):
            raise ValueError("vehicle draw bundle metadata missing")
        relative_manifest = str(bundle.get("manifest_path") or "")
        child_manifest_path = scene_root / relative_manifest
        if not child_manifest_path.is_file():
            raise ValueError("vehicle draw bundle manifest missing")
        expected_manifest_sha = str(bundle.get("manifest_sha256") or "").lower()
        if len(expected_manifest_sha) != 64 or _sha256_file(child_manifest_path) != expected_manifest_sha:
            raise ValueError("vehicle draw bundle manifest SHA-256 mismatch")
        child = json.loads(child_manifest_path.read_text(encoding="utf-8"))
        if not isinstance(child, dict) or child.get("ready") is not True:
            raise ValueError("vehicle draw bundle is not ready")
        artifact = (child.get("artifacts") or {}).get("world_transform")
        if not isinstance(artifact, Mapping) or artifact.get("ready") is not True:
            raise ValueError("vehicle draw has no ready SVWT artifact")
        if artifact.get("format") != SVWT_FORMAT:
            raise ValueError("vehicle draw world-transform artifact format drift")
        packet_path = child_manifest_path.parent / str(artifact.get("path") or "")
        if not packet_path.is_file():
            raise ValueError("vehicle draw SVWT packet missing")
        packet_sha = _sha256_file(packet_path)
        if packet_sha != str(artifact.get("sha256") or "").lower():
            raise ValueError("vehicle draw SVWT packet SHA-256 mismatch")
        matrix = _read_svwt(packet_path)
        if matrix != expected:
            raise ValueError("vehicle draw SVWT matrix disagrees with strict VHF BODY object frame")
        packets.append({
            "draw_order": row.get("draw_order"),
            "submesh_index": row.get("submesh_index"),
            "packet_path": str(packet_path.relative_to(scene_root)),
            "packet_sha256": packet_sha,
            "matrix": matrix,
        })

    result = deepcopy(dict(consumer))
    result.update({
        "status": "ready",
        "ready": True,
        "vulkan_object_frame_ready": True,
        "blocking_reasons": [],
        "OUTPUT": "exact positive Root frame preserved through strict VHF parser ancestry, Phase 645 scene/bootstrap transform, and every Phase 643 Vulkan vehicle SVWT object frame",
        "vulkan_object_frame": {
            "scene_set_format": SCENE_SET_FORMAT,
            "scene_manifest_sha256": _sha256_file(manifest_path),
            "vehicle_draw_count": len(vehicle_rows),
            "svwt_packet_count": len(packets),
            "expected_world_matrix_f32": expected,
            "packets": packets,
        },
    })
    boundary = dict(result.get("boundary") or {})
    boundary.update({
        "phase643_vehicle_svwt_packets_checked": True,
        "runtime_vulkan_static_object_frame_preserved": True,
        "process2_freshness_gated_live_transform_still_required": True,
        "test_only_transform_script_is_retail_motion": False,
        "dynamic_vehicle_world_transform_claimed": False,
    })
    result["boundary"] = boundary
    result["handoff"] = {
        "canonical_BMW_VHF_root_frame_scene_consumer_ready": True,
        "canonical_BMW_VHF_hierarchy_root_frame_ready": True,
        "static_vehicle_render_object_frame_ready": True,
        "process2_freshness_gated_live_transform_required": True,
        "vehicle_world_transform_ready": False,
        "BODY0_bind_frame_proof_ready": False,
        "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
    }
    result["limits"] = {
        "does_not_reprove_process1_root_frame": True,
        "does_not_infer_executable_ownership_from_resource_hierarchy": True,
        "does_not_use_visual_similarity_as_proof": True,
        "does_not_treat_static_vhf_transform_as_dynamic_vehicle_pose": True,
        "does_not_publish_outer_vehicle_vhf_semantic_relation": True,
        "does_not_hide_missing_physics_motion_with_render_animation": True,
        "camera_source_and_timing_remain_process1_process2_owned": True,
    }
    return result

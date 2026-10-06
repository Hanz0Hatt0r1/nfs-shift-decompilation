#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.OuterVehicleBMWVHFRootRelation/1"
DELTA_FORMAT = "SHIFT.OuterVehicleRenderRootDeltaProvenance/1"
BRIDGE_FORMAT = "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1"
DOMAIN_FORMAT = "SHIFT.VehicleRenderModelRootAffineDomainJoin/1"
ROOT_FORMAT = "SHIFT.BMWVHFHierarchyRootFrame/1"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
DECODED_VHF_SHA256 = "e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51"
ROOT_PATH = "CAR[BMW_M3_E36]/NODE[HIERARCHY:Root]"
ROW_CONVENTION = "row-major D3D row-vector affine"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"{label} missing")
    return value


def _matrix16(value: Any, label: str) -> list[float]:
    _require(isinstance(value, Sequence) and not isinstance(value, (str, bytes)), f"{label} must be a sequence")
    _require(len(value) == 16, f"{label} must contain 16 scalars")
    out: list[float] = []
    for item in value:
        _require(not isinstance(item, bool) and isinstance(item, (int, float)), f"{label} contains non-numeric scalar")
        number = float(item)
        _require(math.isfinite(number), f"{label} contains non-finite scalar")
        out.append(number)
    _require(all(abs(out[i]) <= 1e-9 for i in (3, 7, 11)), f"{label} is not row-vector affine")
    _require(abs(out[15] - 1.0) <= 1e-9, f"{label} homogeneous component drift")
    return out


def _mul(a: Sequence[float], b: Sequence[float]) -> list[float]:
    return [sum(float(a[r * 4 + k]) * float(b[k * 4 + c]) for k in range(4)) for r in range(4) for c in range(4)]


def _translation(delta: Sequence[float]) -> list[float]:
    _require(len(delta) == 3, "delta must have three scalars")
    x, y, z = (float(v) for v in delta)
    _require(all(math.isfinite(v) for v in (x, y, z)), "delta contains non-finite scalar")
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        x, y, z, 1.0,
    ]


def _invert4(m: Sequence[float]) -> list[float]:
    rows = [[float(m[r * 4 + c]) for c in range(4)] + [1.0 if r == c else 0.0 for c in range(4)] for r in range(4)]
    for col in range(4):
        pivot = max(range(col, 4), key=lambda r: abs(rows[r][col]))
        _require(abs(rows[pivot][col]) > 1e-12, "relation matrix is singular")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        rows[col] = [v / scale for v in rows[col]]
        for r in range(4):
            if r == col:
                continue
            factor = rows[r][col]
            rows[r] = [x - factor * y for x, y in zip(rows[r], rows[col])]
    return [rows[r][4 + c] for r in range(4) for c in range(4)]


def evaluate_numeric_relation(root_row: Sequence[float], delta_numeric: Sequence[float]) -> tuple[list[float], list[float]]:
    """Pure algebra helper; does not prove numeric delta provenance or open any gate."""
    root = _matrix16(root_row, "BMW VHF root row matrix")
    root_to_outer = _mul(root, _translation(delta_numeric))
    outer_to_root = _invert4(root_to_outer)
    return root_to_outer, outer_to_root


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return _mapping(value, str(path))


def _validate_delta_provenance(delta: Mapping[str, Any]) -> None:
    _require(delta.get("format") == DELTA_FORMAT and delta.get("ready") is True, "render-root delta provenance not positive")
    _require(delta.get("status") == "delta-store-provenance-ready", "render-root delta provenance status drift")
    retail = _mapping(delta.get("retail"), "delta provenance retail")
    _require(retail.get("program") == "SHIFT.exe" and retail.get("md5") == "705af8b420e5eb1e3834ac43d5533c6b", "delta provenance retail identity drift")
    function = _mapping(retail.get("function"), "delta provenance function")
    _require(function.get("address") == "0x00795d60" and function.get("name") == "FUN_00795d60", "delta producer identity drift")
    _require(function.get("size") == 8797 and function.get("calling_convention") == "__fastcall", "delta producer ABI drift")
    _require(function.get("mnemonic_sha256") == "c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14", "delta producer fingerprint drift")
    bridge = _mapping(delta.get("bridge_provenance"), "delta bridge provenance")
    _require(bridge.get("render_root_local_delta_offsets") == ["+0x19c", "+0x1a0", "+0x1a4"], "delta provenance field layout drift")
    analysis = _mapping(delta.get("analysis"), "delta provenance analysis")
    _require(analysis.get("missing_entry_receiver_bytes") == [], "delta provenance byte coverage incomplete")
    _require(analysis.get("structural_blockers") == [], "delta provenance structural blocker remains")
    stores = analysis.get("store_candidates")
    _require(isinstance(stores, list) and bool(stores), "delta provenance store candidates missing")
    covered: set[str] = set()
    for row in stores:
        _require(isinstance(row, Mapping), "delta store candidate malformed")
        if not row.get("render_root_delta_fields_touched"):
            continue
        _require(row.get("target_is_FUN_00795d60_entry_ECX_on_all_reachable_paths") is True, "delta store target not exact entry ECX")
        _require(row.get("outer_Vehicle_delta_field_semantics_joined_from_bridge") is True, "delta store not joined to outer Vehicle field semantics")
        _require(row.get("VHF_frame_semantics_proven") is False, "delta provenance unexpectedly preclaims VHF semantics")
        roots = row.get("terminal_roots")
        _require(isinstance(roots, list) and bool(roots), "delta store terminal value roots missing")
        covered.update(str(v) for v in row.get("render_root_delta_fields_touched") or [])
    _require(covered == {"render_root_delta.x", "render_root_delta.y", "render_root_delta.z"}, "delta provenance does not cover all three semantic fields")
    handoff = _mapping(delta.get("handoff"), "delta provenance handoff")
    _require(handoff.get("render_root_delta_store_provenance_ready") is True, "delta store provenance gate not ready")
    _require(handoff.get("render_root_delta_value_roots_ready") is True, "delta value-root gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is False, "delta provenance preclaims final outer/VHF relation")
    _require(handoff.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is False, "delta provenance preclaims fixed affine relation")


def build_relation(
    delta_provenance: Mapping[str, Any],
    bridge: Mapping[str, Any],
    domain: Mapping[str, Any],
    root: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_delta_provenance(delta_provenance)
    _require(bridge.get("format") == BRIDGE_FORMAT and bridge.get("ready") is True, "outer/render affine bridge not positive")
    outer = _mapping(bridge.get("outer_transform"), "bridge outer_transform")
    snap = _mapping(bridge.get("snapshot_relation"), "bridge snapshot_relation")
    _require(outer.get("render_root_local_delta_offsets") == ["+0x19c", "+0x1a0", "+0x1a4"], "delta field layout drift")
    _require(outer.get("local_delta_has_concrete_setup_producer") is True, "delta setup producer not proven")
    _require(outer.get("local_delta_is_runtime_pose_source") is False, "delta incorrectly classified as runtime pose")
    _require(snap.get("translation_formula") == "P_snapshot = P_outer + R_outer * delta_local", "bridge formula drift")
    _require(snap.get("independent_rotation_source_present") is False, "unexpected independent render-root rotation")

    _require(domain.get("format") == DOMAIN_FORMAT and domain.get("ready") is True, "render-model root-affine domain join not positive")
    proof = _mapping(domain.get("proof"), "domain proof")
    _require(proof.get("vehicle_render_model_root_affine_domain_join_ready") is True, "model/root affine domain not proven")
    participant = _mapping(domain.get("participant_domain"), "participant domain")
    _require(str(participant.get("canonical_bmw_vhf") or "").lower() == CANONICAL_VHF, "canonical BMW VHF domain drift")
    _require(str(participant.get("canonical_bmw_vhf_decoded_sha256") or "").lower() == DECODED_VHF_SHA256, "canonical BMW VHF decoded identity drift")

    _require(root.get("format") == ROOT_FORMAT and root.get("ready") is True, "BMW VHF root frame not positive")
    frame = _mapping(root.get("vehicle_root_frame"), "BMW VHF vehicle_root_frame")
    _require(frame.get("node_type") == "HIERARCHY" and frame.get("node_name") == "Root", "BMW VHF root node identity drift")
    _require(frame.get("node_path") == ROOT_PATH, "BMW VHF root node path drift")
    source = _mapping(root.get("source"), "BMW VHF root source")
    _require(str(source.get("resolved_path") or "").replace("\\", "/").strip("/").lower() == CANONICAL_VHF, "BMW VHF root source path drift")
    _require(str(source.get("decoded_sha256") or "").lower() == DECODED_VHF_SHA256, "BMW VHF root decoded SHA drift")
    provenance = _mapping(root.get("provenance"), "BMW VHF root provenance")
    _require(provenance.get("exact_root_affine_matrix_ready") is True, "BMW VHF root affine matrix not proven")
    matrix_number = str(frame.get("matrix_number") or "")
    _require(bool(matrix_number), "BMW VHF root MatrixNumber missing")
    chain = frame.get("matrix_parent_chain_ids")
    _require(isinstance(chain, list) and bool(chain) and str(chain[-1]) == matrix_number, "BMW VHF root parent chain drift")
    _matrix16(frame.get("world_matrix_row_vector"), "BMW VHF root row matrix")

    relation: dict[str, Any] = {
        "kind": "fixed_affine",
        "semantic_authority": "Process 1",
        "source_frame": "outer_vehicle_root",
        "target_frame": "canonical_bmw_vhf_hierarchy_root",
        "matrix_convention": ROW_CONVENTION,
        "delta_local_source": ["outerVehicle+0x19c", "outerVehicle+0x1a0", "outerVehicle+0x1a4"],
        "delta_value_root_contract": DELTA_FORMAT,
        "delta_producer": "FUN_00795d60",
        "fixed_scope": "per initialized vehicle instance after Vehicle::InitVehicle; invariant with respect to per-frame outer pose",
        "model_to_outer_formula": "T(delta_local)",
        "vhf_root_to_outer_formula": "M_vhf_root_to_model * T(delta_local)",
        "outer_to_vhf_root_formula": "inverse(M_vhf_root_to_model * T(delta_local))",
        "identity_semantics_proven": False,
        "relation_matrix_numeric_ready": False,
    }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "outer-vehicle-bmw-vhf-fixed-affine-relation-proven",
        "ready": True,
        "subject": {
            "vehicle": "BMW_M3_E36",
            "canonical_vhf": CANONICAL_VHF,
            "decoded_sha256": DECODED_VHF_SHA256,
            "root_node_path": ROOT_PATH,
            "matrix_number": matrix_number,
            "matrix_parent_chain_ids": [str(v) for v in chain],
            "root_frame_contract": ROOT_FORMAT,
        },
        "inputs": {
            "outer_delta_provenance": DELTA_FORMAT,
            "outer_render_affine_bridge": BRIDGE_FORMAT,
            "render_model_affine_domain": DOMAIN_FORMAT,
            "vhf_root_frame": ROOT_FORMAT,
        },
        "relation": relation,
        "proof": {
            "render_root_affine_is_canonical_bmw_vhf_model_domain": True,
            "delta_is_setup_state_not_runtime_pose": True,
            "vhf_root_resolved_matrix_is_local_to_model_domain": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
        },
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "consumer": "Process 1 BMW BODY0 bind-frame composition; Process 2 numeric relation admission after delta materialization",
        },
        "limits": {
            "numeric_delta_invented": False,
            "identity_inferred_from_numeric_equality": False,
            "identity_vhf_root_matrix_implies_outer_identity": False,
            "process2_numeric_relation_admission_ready": False,
            "runtime_capture_required": False,
            "original_game_executed": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("delta_provenance", type=Path)
    ap.add_argument("bridge", type=Path)
    ap.add_argument("domain", type=Path)
    ap.add_argument("root", type=Path)
    ap.add_argument("--json-out", type=Path)
    ns = ap.parse_args()
    report = build_relation(_load(ns.delta_provenance), _load(ns.bridge), _load(ns.domain), _load(ns.root))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if ns.json_out:
        ns.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")

if __name__ == "__main__":
    main()

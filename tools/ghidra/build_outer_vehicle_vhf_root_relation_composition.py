#!/usr/bin/env python3
"""Compose the proven outer/render affine domain with the exact BMW VHF root frame.

This Process 1 helper proves only the *formula* for the remaining fixed frame
relation. It never fabricates numeric FUN_00795d60 +0x19c/+0x1a0/+0x1a4
values. A later numeric producer may materialize the formula into the final
outer->VHF matrix.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.OuterVehicleVHFRootRelationComposition/1"
DOMAIN_FORMAT = "SHIFT.VehicleRenderModelRootAffineDomainJoin/1"
ROOT_FORMAT = "SHIFT.BMWVHFHierarchyRootFrame/1"
BRIDGE_FORMAT = "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1"
DELTA_FORMAT = "SHIFT.OuterVehicleRenderRootDeltaProvenance/1"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
DECODED_SHA256 = "e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51"
DELTA_OFFSETS = ["+0x19c", "+0x1a0", "+0x1a4"]
DELTA_FIELD_LABELS = ["render_root_delta.x", "render_root_delta.y", "render_root_delta.z"]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, Mapping), f"{path}: expected JSON object")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"{label} missing")
    return value


def _matrix(value: Any, label: str) -> list[float]:
    _require(isinstance(value, list) and len(value) == 16, f"{label}: expected 16 scalars")
    result: list[float] = []
    for raw in value:
        _require(not isinstance(raw, bool), f"{label}: boolean scalar")
        try:
            number = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}: non-numeric scalar") from exc
        _require(math.isfinite(number), f"{label}: non-finite scalar")
        result.append(number)
    _require(all(abs(result[index]) <= 1.0e-9 for index in (3, 7, 11)), f"{label}: not D3D row-vector affine")
    _require(abs(result[15] - 1.0) <= 1.0e-9, f"{label}: affine w drift")
    return result


def _det3(m: Sequence[float]) -> float:
    return (
        m[0] * (m[5] * m[10] - m[6] * m[9])
        - m[1] * (m[4] * m[10] - m[6] * m[8])
        + m[2] * (m[4] * m[9] - m[5] * m[8])
    )


def _inverse_row_affine(m: Sequence[float]) -> list[float]:
    det = _det3(m)
    _require(abs(det) > 1.0e-12, "BMW VHF root row matrix is singular")
    invdet = 1.0 / det
    r = [
        (m[5] * m[10] - m[6] * m[9]) * invdet,
        (m[2] * m[9] - m[1] * m[10]) * invdet,
        (m[1] * m[6] - m[2] * m[5]) * invdet,
        (m[6] * m[8] - m[4] * m[10]) * invdet,
        (m[0] * m[10] - m[2] * m[8]) * invdet,
        (m[2] * m[4] - m[0] * m[6]) * invdet,
        (m[4] * m[9] - m[5] * m[8]) * invdet,
        (m[1] * m[8] - m[0] * m[9]) * invdet,
        (m[0] * m[5] - m[1] * m[4]) * invdet,
    ]
    tx, ty, tz = m[12], m[13], m[14]
    itx = -(tx * r[0] + ty * r[3] + tz * r[6])
    ity = -(tx * r[1] + ty * r[4] + tz * r[7])
    itz = -(tx * r[2] + ty * r[5] + tz * r[8])
    return [
        r[0], r[1], r[2], 0.0,
        r[3], r[4], r[5], 0.0,
        r[6], r[7], r[8], 0.0,
        itx, ity, itz, 1.0,
    ]


def _is_identity(m: Sequence[float]) -> bool:
    ident = [1.0,0.0,0.0,0.0, 0.0,1.0,0.0,0.0, 0.0,0.0,1.0,0.0, 0.0,0.0,0.0,1.0]
    return all(abs(a-b) <= 1.0e-9 for a,b in zip(m, ident))


def _validate_domain(value: Mapping[str, Any]) -> None:
    _require(value.get("format") == DOMAIN_FORMAT and value.get("ready") is True, "root-affine domain join is not positive")
    proof = _mapping(value.get("proof"), "root-affine domain proof")
    _require(proof.get("vehicle_render_model_root_affine_domain_join_ready") is True, "root-affine domain proof gate not ready")
    participant = _mapping(value.get("participant_domain"), "participant domain")
    _require(participant.get("canonical_bmw_vhf") == CANONICAL_VHF, "domain canonical VHF path drift")
    _require(participant.get("canonical_bmw_vhf_decoded_sha256") == DECODED_SHA256, "domain BMW VHF SHA drift")
    handoff = _mapping(value.get("handoff"), "domain handoff")
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is False, "domain join preclaims outer/VHF relation")
    _require(handoff.get("BODY0_bind_frame_proof_ready") is False, "domain join preclaims BODY0 bind")


def _validate_bridge(value: Mapping[str, Any]) -> None:
    _require(value.get("format") == BRIDGE_FORMAT and value.get("ready") is True, "outer/render affine bridge is not positive")
    outer = _mapping(value.get("outer_transform"), "bridge outer transform")
    _require(outer.get("render_root_local_delta_offsets") == DELTA_OFFSETS, "render-root delta layout drift")
    _require(outer.get("local_delta_has_concrete_setup_producer") is True, "render-root delta setup producer not proven")
    _require(outer.get("local_delta_is_runtime_pose_source") is False, "render-root delta misclassified as runtime pose")
    snapshot = _mapping(value.get("snapshot_relation"), "bridge snapshot relation")
    _require(snapshot.get("translation_formula") == "P_snapshot = P_outer + R_outer * delta_local", "outer/render translation formula drift")
    _require(snapshot.get("independent_rotation_source_present") is False, "unexpected independent render-root rotation")
    handoff = _mapping(value.get("handoff"), "bridge handoff")
    _require(handoff.get("outer_vehicle_to_render_root_symbolic_affine_ready") is True, "outer/render symbolic affine not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is False, "bridge preclaims outer/VHF relation")


def _validate_root(value: Mapping[str, Any]) -> tuple[Mapping[str, Any], list[float]]:
    _require(value.get("format") == ROOT_FORMAT and value.get("ready") is True, "BMW VHF root frame is not positive")
    source = _mapping(value.get("source"), "BMW VHF root source")
    _require(source.get("resolved_path") == CANONICAL_VHF, "BMW VHF root canonical path drift")
    _require(source.get("decoded_sha256") == DECODED_SHA256, "BMW VHF root decoded SHA drift")
    frame = _mapping(value.get("vehicle_root_frame"), "BMW VHF root frame")
    _require(frame.get("node_type") == "HIERARCHY" and frame.get("node_name") == "Root", "BMW VHF HIERARCHY Root identity drift")
    _require(bool(str(frame.get("matrix_number") or "")), "BMW VHF Root MatrixNumber missing")
    chain = frame.get("matrix_parent_chain_ids")
    _require(isinstance(chain, list) and chain and chain[-1] == str(frame.get("matrix_number")), "BMW VHF Root parent-chain drift")
    row = _matrix(frame.get("world_matrix_row_vector"), "BMW VHF Root world row matrix")
    handoff = _mapping(value.get("handoff"), "BMW VHF root handoff")
    _require(handoff.get("canonical_BMW_VHF_hierarchy_root_frame_ready") is True, "BMW VHF root-frame gate not ready")
    _require(handoff.get("canonical_BMW_VHF_hierarchy_root_matrix_ready") is True, "BMW VHF root-matrix gate not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is False, "root frame preclaims outer/VHF relation")
    return frame, row


def _validate_delta(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    _require(value.get("format") == DELTA_FORMAT and value.get("ready") is True, "render-root delta provenance is not positive")
    retail = _mapping(value.get("retail"), "delta provenance retail")
    function = _mapping(retail.get("function"), "delta provenance target function")
    _require(function.get("address") == "0x00795d60", "delta provenance target address drift")
    bridge = _mapping(value.get("bridge_provenance"), "delta bridge provenance")
    _require(bridge.get("translation_formula") == "P_snapshot = P_outer + R_outer * delta_local", "delta bridge formula drift")
    analysis = _mapping(value.get("analysis"), "delta analysis")
    _require(analysis.get("missing_entry_receiver_bytes") == [], "delta field coverage incomplete")
    rows = analysis.get("store_candidates")
    _require(isinstance(rows, list) and rows, "delta STORE candidates missing")
    covered: set[str] = set()
    for row in rows:
        _require(isinstance(row, Mapping), "invalid delta STORE candidate")
        if row.get("target_is_FUN_00795d60_entry_ECX_on_all_reachable_paths") is not True:
            continue
        fields = row.get("render_root_delta_fields_touched")
        if isinstance(fields, list):
            covered.update(str(field) for field in fields)
    _require(covered == set(DELTA_FIELD_LABELS), f"delta field semantic coverage drift: {sorted(covered)}")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def build(domain: Mapping[str, Any], bridge: Mapping[str, Any], root: Mapping[str, Any], delta: Mapping[str, Any]) -> dict[str, Any]:
    _validate_domain(domain)
    _validate_bridge(bridge)
    frame, root_row = _validate_root(root)
    store_rows = _validate_delta(delta)
    root_inverse = _inverse_row_affine(root_row)
    numeric_delta_ready = all(
        any(
            offset in (row.get("render_root_delta_fields_touched") or [])
            and row.get("numeric_delta_value_proven") is True
            for row in store_rows
        )
        for offset in DELTA_FIELD_LABELS
    )
    # Current /1 delta-provenance intentionally cannot make this true. Preserve
    # the condition explicitly so a later numeric producer must carry a new,
    # source-backed contract rather than silently extending this schema.
    _require(numeric_delta_ready is False, "unexpected numeric delta promotion inside /1 provenance; bind an explicit numeric producer contract instead")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "outer-vhf-fixed-affine-formula-proven-numeric-delta-pending",
        "ready": True,
        "inputs": {
            "root_affine_domain": DOMAIN_FORMAT,
            "outer_render_affine_bridge": BRIDGE_FORMAT,
            "render_root_delta_provenance": DELTA_FORMAT,
            "bmw_vhf_hierarchy_root_frame": ROOT_FORMAT,
        },
        "subjects": {
            "canonical_vhf": CANONICAL_VHF,
            "decoded_sha256": DECODED_SHA256,
            "vhf_root": {
                "node_type": "HIERARCHY",
                "node_name": "Root",
                "matrix_number": str(frame.get("matrix_number")),
                "matrix_parent_chain_ids": list(frame.get("matrix_parent_chain_ids")),
            },
            "outer_render_delta_fields": DELTA_OFFSETS,
        },
        "composition": {
            "convention": "row-major D3D row-vector affine",
            "render_root_world_from_outer_world": "M_render_world = T_row(delta_local) * M_outer_world",
            "vhf_root_world_from_render_world": "M_vhf_root_world = M_vhf_root_model * M_render_world",
            "vhf_root_world_from_outer_world": "M_vhf_root_world = M_vhf_root_model * T_row(delta_local) * M_outer_world",
            "vhf_root_local_to_outer_local": "M_vhf_to_outer = M_vhf_root_model * T_row(delta_local)",
            "outer_local_to_vhf_root_local": "M_outer_to_vhf = T_row(-delta_local) * inverse(M_vhf_root_model)",
            "root_model_row_matrix": root_row,
            "inverse_root_model_row_matrix": root_inverse,
            "root_model_matrix_is_identity": _is_identity(root_row),
            "delta_local_symbolic": ["outerVehicle+0x19c", "outerVehicle+0x1a0", "outerVehicle+0x1a4"],
            "multiplication_order_proven": True,
            "formula_ready": True,
        },
        "provenance": {
            "same_canonical_vhf_subject_across_domain_and_root": True,
            "participant_root_is_local_to_world_for_canonical_vhf_model_domain": True,
            "outer_to_render_root_fixed_setup_affine_ready": True,
            "exact_vhf_root_local_to_model_affine_ready": True,
            "fun_00795d60_exact_entry_receiver_delta_stores_ready": True,
        },
        "handoff": {
            "outer_vehicle_to_VHF_root_fixed_affine_formula_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "outer_vehicle_root_to_VHF_numeric_matrix_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "next_frontier": "materialize exact source-backed numeric FUN_00795d60 delta_local for BMW, then evaluate T_row(-delta_local) * inverse(M_vhf_root_model)",
        },
        "blockers": [{
            "id": "bmw-fun-00795d60-render-root-delta-numeric-materialization",
            "required_evidence": "source-backed numeric values for outerVehicle +0x19c/+0x1a0/+0x1a4 under the exact BMW setup; do not guess from identity VHF root, visual alignment, or host runtime",
        }],
        "limits": {
            "numeric_delta_guessed": False,
            "identity_root_matrix_used_as_outer_vhf_identity": False,
            "outer_vehicle_root_to_VHF_relation_promoted": False,
            "BODY0_bind_frame_claimed": False,
            "runtime_capture_required": False,
            "original_game_executed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("domain", type=Path)
    parser.add_argument("bridge", type=Path)
    parser.add_argument("root_frame", type=Path)
    parser.add_argument("delta_provenance", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = build(_load(args.domain), _load(args.bridge), _load(args.root_frame), _load(args.delta_provenance))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Join the proven BMW vehicle physics text resources into one neutral profile.

The graph reflects only loader boundaries established in SHIFT.exe.c:
CDF is the chassis root, EDF supplies external engine data, GDF the gearbox
ratio tables, and SDF the rigid-body suspension model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from engine_edf_runtime import parse_engine_edf
from gearbox_gdf_runtime import parse_gdf
from rigid_body_sdf_runtime import (
    compile_sdf_runtime_topology,
    build_sdf_constraint_connectivity_matrix,
    compile_sdf_constraint_solver_graph_from_report,
    describe_sdf_constraint_runtime_lowering,
    optimize_sdf_constraint_order,
    parse_sdf,
    resolve_sdf_body_references,
)
from vehicle_cdf_runtime import parse_cdf
from sdf_constraint_solver_runtime import describe_sdf_sparse_solver_contract, validate_sdf_solver_contract
from sdf_constraint_solver_frame_runtime import (
    derive_builtin_diagonal_reset_nodes,
    describe_sdf_solver_frame_contract,
    validate_sdf_solver_frame_profile,
)
from sdf_body_accumulator_runtime import describe_sdf_body_accumulator_contract
from sdf_body_impulse_runtime import describe_sdf_body_impulse_primitives
from sdf_body_solver_export_runtime import describe_sdf_body_solver_export_contract
from sdf_body_tensor_runtime import describe_sdf_body_tensor_contract
from sdf_body_state_primitives_runtime import describe_sdf_body_state_primitives
from sdf_body_frame_runtime import describe_sdf_body_frame_contract
from sdf_constraint_projection_runtime import (
    describe_hinge_projection_provenance,
    describe_joint_projection_provenance,
)
from sdf_body_state_projection_runtime import describe_sdf_body_state_projection_contract
from sdf_hinge_matrix_coupling_runtime import describe_hinge_matrix_coupling_contract
from sdf_bar_matrix_coupling_runtime import describe_bar_matrix_coupling_contract
from sdf_joint_matrix_coupling_runtime import describe_joint_matrix_coupling_contract
from sdf_hinge_bar_matrix_coupling_runtime import describe_hinge_bar_matrix_coupling_contract
from sdf_post_solve_runtime import describe_post_solve_application_contract
from bmw_m3_e36_solver_domain_runtime import build_solver_domain
from sdf_constraint_matrix_assembly_runtime import materialize_source_seed_matrix
from sdf_constraint_matrix_assembly_runtime import describe_sdf_constraint_matrix_assembly_contract
from sdf_constraint_matrix_assembly_runtime import build_retail_matrix_storage
from sdf_full_frame_runtime import describe_full_frame_contract
from sdf_solver_frame_verification_runtime import describe_solver_frame_verification_contract
from sdf_solver_capture_runtime import describe_sdf_solver_capture_contract
from sdf_solver_capture_binary_runtime import describe_sdf_solver_capture_binary_contract
from bmw_m3_solver_capture_verify_runtime import describe_bmw_m3_solver_capture_verifier
from sdf_runtime_probe_runtime import describe_sdf_runtime_probe_contract
from sdf_runtime_probe_session_runtime import describe_sdf_runtime_probe_session_contract
from sdf_runtime_probe_pe_validation import describe_probe_pe_validation_contract
from sdf_runtime_probe_launcher_runtime import describe_sdf_runtime_probe_launcher

FORMAT = "SHIFT.VehiclePhysicsAssetGraph/1"


def _read(path: str | Path) -> tuple[Path, bytes]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    return p, p.read_bytes()


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_profile(
    *,
    cdf: str | Path,
    edf: str | Path,
    gdf: str | Path,
    sdf: str | Path,
    strict: bool = False,
) -> dict[str, Any]:
    resources = {}
    for kind, path in (("cdf", cdf), ("edf", edf), ("gdf", gdf), ("sdf", sdf)):
        source, data = _read(path)
        resources[kind] = {
            "path": str(source),
            "filename": source.name,
            "bytes": len(data),
            "sha256": _hash(data),
        }

    cdf_report = parse_cdf(Path(cdf).read_bytes(), strict=strict)
    edf_report = parse_engine_edf(Path(edf).read_bytes(), strict=strict)
    gdf_report = parse_gdf(Path(gdf).read_bytes(), strict=strict)
    sdf_report = parse_sdf(Path(sdf).read_bytes(), strict=strict)
    sdf_graph = resolve_sdf_body_references(sdf_report)
    sdf_runtime_topology = compile_sdf_runtime_topology(sdf_report)
    sdf_constraint_runtime = describe_sdf_constraint_runtime_lowering(sdf_report)
    sdf_constraint_connectivity = build_sdf_constraint_connectivity_matrix(sdf_report)
    sdf_constraint_order = optimize_sdf_constraint_order(sdf_report)
    sdf_constraint_solver_graph = compile_sdf_constraint_solver_graph_from_report(sdf_report)
    sdf_solver_contract = describe_sdf_sparse_solver_contract(
        constraint_count=sdf_constraint_solver_graph.get("constraint_count")
    )
    sdf_solver_validation = validate_sdf_solver_contract(sdf_constraint_solver_graph)
    sdf_solver_frame = describe_sdf_solver_frame_contract(
        solver_scalar_count=sdf_constraint_solver_graph.get("solver_scalar_count"),
        body_count=sdf_report.get("topology", {}).get("body_count"),
    )
    sdf_diagonal_reset = derive_builtin_diagonal_reset_nodes(
        sdf_constraint_solver_graph.get("scalar_connectivity", {})
    )
    sdf_body_accumulator = describe_sdf_body_accumulator_contract()
    sdf_body_impulse = describe_sdf_body_impulse_primitives()
    sdf_body_solver_export = describe_sdf_body_solver_export_contract()
    sdf_body_tensor = describe_sdf_body_tensor_contract()
    sdf_body_state_primitives = describe_sdf_body_state_primitives()
    sdf_body_frame = describe_sdf_body_frame_contract()
    sdf_joint_projection = describe_joint_projection_provenance()
    sdf_hinge_projection = describe_hinge_projection_provenance()
    sdf_body_state_projection = describe_sdf_body_state_projection_contract()
    sdf_hinge_matrix_coupling = describe_hinge_matrix_coupling_contract()
    sdf_bar_matrix_coupling = describe_bar_matrix_coupling_contract()
    sdf_joint_matrix_coupling = describe_joint_matrix_coupling_contract()
    sdf_joint_d15_source_audit = {
        "ready": True,
        "function": "FUN_007bbb80",
        "expression": "d15 = m00*y - m01*x",
        "source_offsets": ["+0xb0", "+0xbc"],
    }
    sdf_hinge_bar_matrix_coupling = describe_hinge_bar_matrix_coupling_contract()
    sdf_post_solve = describe_post_solve_application_contract()
    sdf_matrix_assembly = describe_sdf_constraint_matrix_assembly_contract()
    sdf_matrix_storage = build_retail_matrix_storage(
        sdf_constraint_solver_graph.get("solver_scalar_count", 0)
    )
    sdf_real_solver_domain = build_solver_domain(sdf_report)
    sdf_matrix_seed_write = materialize_source_seed_matrix(
        sdf_constraint_solver_graph.get("scalar_connectivity", {})
    )
    sdf_full_frame = describe_full_frame_contract(
        solver_scalar_count=sdf_constraint_solver_graph.get("solver_scalar_count"),
        body_count=sdf_report.get("topology", {}).get("body_count"),
        runtime_flags_available=False,
    )
    sdf_frame_verification = describe_solver_frame_verification_contract()
    sdf_solver_capture = describe_sdf_solver_capture_contract()
    sdf_solver_capture_binary = describe_sdf_solver_capture_binary_contract()
    bmw_m3_solver_capture_verifier = describe_bmw_m3_solver_capture_verifier()
    sdf_runtime_probe = describe_sdf_runtime_probe_contract()
    sdf_runtime_probe_session = describe_sdf_runtime_probe_session_contract()
    sdf_runtime_probe_pe = describe_probe_pe_validation_contract()
    sdf_probe_launcher = describe_sdf_runtime_probe_launcher()

    blockers: list[str] = []
    for name, report in (
        ("cdf", cdf_report),
        ("edf", edf_report),
        ("gdf", gdf_report),
        ("sdf", sdf_report),
    ):
        if report.get("ready") is not True:
            blockers.append(f"{name}:parse-not-ready")
        blockers.extend(
            f"{name}:{reason}" for reason in report.get("warnings") or []
        )
    blockers.extend(f"sdf-graph:{reason}" for reason in sdf_graph.get("unresolved") or [])
    blockers.extend(f"sdf-runtime:{reason}" for reason in sdf_runtime_topology.get("unresolved") or [])
    blockers.extend(f"sdf-constraint-runtime:{reason}" for reason in sdf_constraint_runtime.get("unresolved") or [])
    blockers.extend(f"sdf-constraint-connectivity:{reason}" for reason in sdf_constraint_connectivity.get("unresolved") or [])
    blockers.extend(f"sdf-constraint-order:{reason}" for reason in sdf_constraint_order.get("unresolved") or [])
    blockers.extend(f"sdf-constraint-solver:{reason}" for reason in sdf_constraint_solver_graph.get("unresolved") or [])
    blockers.extend(f"sdf-solver-contract:{reason}" for reason in sdf_solver_validation.get("errors") or [])
    sdf_frame_validation = validate_sdf_solver_frame_profile({
        "summary": {
            "sdf_solver_scalar_count": sdf_constraint_solver_graph.get("solver_scalar_count"),
            "sdf_constraint_solver_graph_ready": sdf_constraint_solver_graph.get("ready") is True,
            "sdf_sparse_solver_contract_ready": sdf_solver_contract.get("ready") is True,
        }
    })
    blockers.extend(f"sdf-solver-frame:{reason}" for reason in sdf_frame_validation.get("errors") or [])

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not blockers else "ready-with-warnings",
        "ready": not blockers,
        "resources": resources,
        "load_graph": {
            "chassis": {
                "format": cdf_report["format"],
                "runtime_loader": "FUN_0074d640 -> FUN_007be420",
                "role": "vehicle chassis CDF",
            },
            "engine": {
                "format": edf_report["format"],
                "runtime_loader": "FUN_007c3280",
                "role": "external ENGINE/EDF",
            },
            "gearbox": {
                "format": gdf_report["format"],
                "runtime_loader": "FUN_007c2110",
                "role": "external gearbox GDF",
            },
            "suspension": {
                "format": sdf_report["format"],
                "runtime_loader": "FUN_007bf790 -> FUN_007b6900",
                "role": "rigid-body suspension SDF",
            },
        },
        "summary": {
            "cdf_sections": cdf_report.get("section_count", 0),
            "cdf_entries": cdf_report.get("entry_count", 0),
            "cdf_unknown_entries": cdf_report.get("unknown_entry_count", 0),
            "edf_entries": edf_report.get("entry_count", 0),
            "edf_unknown_entries": edf_report.get("unknown_entry_count", 0),
            "edf_rpm_torque_points": edf_report.get("rpm_torque", {}).get("point_count", 0),
            "gdf_gear_ratio_count": gdf_report.get("gear_ratio_count", 0),
            "gdf_final_drive_ratio_count": gdf_report.get("final_drive_ratio_count", 0),
            "gdf_sorted_ratio_count": len(gdf_report.get("sorted_gear_ratios", [])),
            "sdf_bodies": sdf_report.get("topology", {}).get("body_count", 0),
            "sdf_joint_hinge_count": sdf_report.get("topology", {}).get("joint_hinge_count", 0),
            "sdf_bar_count": sdf_report.get("topology", {}).get("bar_count", 0),
            "sdf_body_reference_ready": sdf_graph.get("ready") is True,
            "sdf_body_count": len(sdf_graph.get("body_names", [])),
            "sdf_constraint_count": sdf_graph.get("edge_count", 0),
            "sdf_runtime_topology_ready": sdf_runtime_topology.get("ready") is True,
            "sdf_runtime_constraint_count": sdf_runtime_topology.get("constraint_count", 0),
            "sdf_constraint_runtime_lowering_ready": sdf_constraint_runtime.get("ready") is True,
            "sdf_constraint_runtime_record_count": sdf_constraint_runtime.get("record_count", 0),
            "sdf_constraint_shared_body_pair_count": sdf_constraint_connectivity.get("shared_body_pair_count", 0),
            "sdf_constraint_order_final_cost": sdf_constraint_order.get("final_cost"),
            "sdf_constraint_solver_graph_ready": sdf_constraint_solver_graph.get("ready") is True,
            "sdf_constraint_solver_edge_record_count": sdf_constraint_solver_graph.get("allocations", {}).get("edge_record_count", 0),
            "sdf_solver_scalar_count": sdf_constraint_solver_graph.get("solver_scalar_count", sdf_constraint_solver_graph.get("constraint_count", 0)),
            "sdf_sparse_solver_contract_ready": sdf_solver_contract.get("ready") is True,
            "sdf_sparse_solver_validation_ready": sdf_solver_validation.get("ready") is True,
            "sdf_solver_frame_contract_ready": sdf_solver_frame.get("ready") is True,
            "sdf_solver_frame_validation_ready": sdf_frame_validation.get("ready") is True,
            "sdf_builtin_diagonal_reset_node_count": len(
                sdf_diagonal_reset.get("unique_scalar_nodes") or []
            ),
            "sdf_body_accumulator_contract_ready": sdf_body_accumulator.get("ready") is True,
            "sdf_body_impulse_primitives_ready": sdf_body_impulse.get("ready") is True,
            "sdf_body_solver_export_ready": sdf_body_solver_export.get("ready") is True,
            "sdf_body_tensor_ready": sdf_body_tensor.get("ready") is True,
            "sdf_body_state_primitives_ready": sdf_body_state_primitives.get("ready") is True,
            "sdf_body_frame_ready": sdf_body_frame.get("ready") is True,
            "sdf_joint_projection_ready": sdf_joint_projection.get("ready") is True,
            "sdf_hinge_projection_ready": sdf_hinge_projection.get("ready") is True,
            "sdf_body_state_projection_contract_ready": sdf_body_state_projection.get("ready") is True,
            "sdf_hinge_matrix_coupling_ready": sdf_hinge_matrix_coupling.get("ready") is True,
            "sdf_bar_matrix_coupling_ready": sdf_bar_matrix_coupling.get("ready") is True,
            "sdf_joint_matrix_coupling_ready": sdf_joint_matrix_coupling.get("ready") is True,
            "sdf_joint_d15_source_audit_ready": sdf_joint_d15_source_audit.get("ready") is True,
            "sdf_hinge_bar_matrix_coupling_ready": sdf_hinge_bar_matrix_coupling.get("ready") is True,
            "sdf_post_solve_application_ready": sdf_post_solve.get("ready") is True,
            "sdf_matrix_assembly_ready": sdf_matrix_assembly.get("ready") is True,
            "sdf_matrix_storage_ready": sdf_matrix_storage.get("ready") is True,
            "sdf_real_solver_domain_ready": sdf_real_solver_domain.get("ready") is True,
            "sdf_real_solver_scalar_count": sdf_real_solver_domain.get("solver_scalar_count", 0),
            "sdf_matrix_seed_write_ready": sdf_matrix_seed_write.get("ready") is True,
            "sdf_matrix_seed_write_count": sdf_matrix_seed_write.get("write_count", 0),
            "sdf_full_frame_contract_ready": sdf_full_frame.get("ready") is True,
            "sdf_solver_frame_verification_ready": sdf_frame_verification.get("ready") is True,
            "sdf_full_frame_runtime_ready": sdf_full_frame.get("status") == "runtime-complete",
            "sdf_solver_capture_contract_ready": sdf_solver_capture.get("ready") is True,
            "sdf_solver_capture_binary_contract_ready": sdf_solver_capture_binary.get("ready") is True,
            "bmw_m3_solver_capture_verifier_ready": bmw_m3_solver_capture_verifier.get("ready") is True,
            "sdf_runtime_probe_ready": sdf_runtime_probe.get("ready") is True,
            "sdf_runtime_probe_session_ready": sdf_runtime_probe_session.get("ready") is True,
            "sdf_runtime_probe_pe_ready": sdf_runtime_probe_pe.get("ready") is True,
            "sdf_runtime_probe_launcher_ready": sdf_probe_launcher.get("ready") is True,
        },
        "details": {
            "cdf": cdf_report,
            "edf": edf_report,
            "gdf": gdf_report,
            "sdf": sdf_report,
            "sdf_reference_graph": sdf_graph,
            "sdf_runtime_topology": sdf_runtime_topology,
            "sdf_constraint_runtime": sdf_constraint_runtime,
            "sdf_constraint_connectivity": sdf_constraint_connectivity,
            "sdf_constraint_order": sdf_constraint_order,
            "sdf_constraint_solver_graph": sdf_constraint_solver_graph,
            "sdf_sparse_solver_contract": sdf_solver_contract,
            "sdf_sparse_solver_validation": sdf_solver_validation,
            "sdf_solver_frame": sdf_solver_frame,
            "sdf_solver_frame_validation": sdf_frame_validation,
            "sdf_builtin_diagonal_reset": sdf_diagonal_reset,
            "sdf_body_accumulator": sdf_body_accumulator,
            "sdf_body_impulse_primitives": sdf_body_impulse,
            "sdf_body_solver_export": sdf_body_solver_export,
            "sdf_body_tensor": sdf_body_tensor,
            "sdf_body_state_primitives": sdf_body_state_primitives,
            "sdf_body_frame": sdf_body_frame,
            "sdf_joint_projection": sdf_joint_projection,
            "sdf_hinge_projection": sdf_hinge_projection,
            "sdf_body_state_projection": sdf_body_state_projection,
            "sdf_hinge_matrix_coupling": sdf_hinge_matrix_coupling,
            "sdf_bar_matrix_coupling": sdf_bar_matrix_coupling,
            "sdf_joint_matrix_coupling": sdf_joint_matrix_coupling,
            "sdf_joint_d15_source_audit": sdf_joint_d15_source_audit,
            "sdf_hinge_bar_matrix_coupling": sdf_hinge_bar_matrix_coupling,
            "sdf_post_solve_application": sdf_post_solve,
            "sdf_matrix_assembly": sdf_matrix_assembly,
            "sdf_matrix_storage": sdf_matrix_storage,
            "sdf_real_solver_domain": sdf_real_solver_domain,
            "sdf_matrix_seed_write": sdf_matrix_seed_write,
            "sdf_full_frame": sdf_full_frame,
            "sdf_solver_frame_verification": sdf_frame_verification,
            "sdf_solver_capture": sdf_solver_capture,
            "sdf_solver_capture_binary": sdf_solver_capture_binary,
            "bmw_m3_solver_capture_verifier": bmw_m3_solver_capture_verifier,
            "sdf_runtime_probe": sdf_runtime_probe,
            "sdf_runtime_probe_session": sdf_runtime_probe_session,
            "sdf_runtime_probe_pe": sdf_runtime_probe_pe,
            "sdf_runtime_probe_launcher": sdf_probe_launcher,
        },
        "blockers": list(dict.fromkeys(blockers)),
        "evidence": {
            "cdf_to_engine": "external engine resource selected by FUN_007c3280",
            "cdf_to_gearbox": "GDF root consumed by FUN_007c2110",
            "cdf_to_suspension": "SDF root consumed by FUN_007bf790",
            "no_cross_file_value_inference": True,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a neutral vehicle physics asset graph from CDF/EDF/GDF/SDF")
    parser.add_argument("cdf", type=Path)
    parser.add_argument("edf", type=Path)
    parser.add_argument("gdf", type=Path)
    parser.add_argument("sdf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    report = build_profile(cdf=args.cdf, edf=args.edf, gdf=args.gdf, sdf=args.sdf, strict=args.strict)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"format": report["format"], "status": report["status"], "ready": report["ready"], "summary": report["summary"], "blockers": report["blockers"]}, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compose the proven global vehicle component base with the outer-update receiver.

This deliberately does not identify the anonymous *record+0x340 update child as
the vehicle.  Phase 633/635/636 already establish a separate vehicle pointer
lane: the runtime FUN_00757d2c callsite uses ECX=0x00c13700 as its vehicle base,
while the outer-update callsite contract independently uses &DAT_00c13700.
The remaining BODY-pose blocker is therefore downstream receiver/owner
continuity, not update-child pointer equality.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.GlobalVehicleComponentBaseIdentity/1"
OUTER_FORMAT = "SHIFT.OuterUpdateCallsiteStatic/1"
VEHICLE_FRONTIER_FORMAT = "SHIFT.VehicleBodyIdentityFrontier/1"
CALLSITE_FORMAT = "SHIFT.GlobalVehicleComponentCallsiteStatic/1"

SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
GLOBAL_VEHICLE_ADDRESS = 0x00C13700
OUTER_UPDATE = "0x00770e80"
HALF_STEP = "0x00765470"
BODY_ARRAY_LOOP = "0x007b2270"
RUNTIME_CALL = 0x0079A5BC
RUNTIME_RETURN = 0x0079A5C1
RUNTIME_CALLER = "FUN_0079a050"
MUTATION_CORE = 0x00757D2C
SOLVER_SETUP = "0x007615c0"


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"invalid integer: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError(f"invalid integer: {value!r}")


def _dat_symbol_address(value: Any) -> int:
    if not isinstance(value, str):
        raise ValueError("outer receiver symbol missing")
    match = re.fullmatch(r"&?DAT_([0-9A-Fa-f]{8})", value.strip())
    if match is None:
        raise ValueError(f"unsupported outer receiver symbol: {value!r}")
    return int(match.group(1), 16)


def _probe_module():
    path = Path(__file__).resolve().parents[2] / "src" / "physics" / "sdf_runtime_probe_runtime.py"
    spec = importlib.util.spec_from_file_location("sdf_runtime_probe_for_global_vehicle_identity", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load probe contract: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_global_vehicle_component_base_identity(
    outer_callsite_path: Path,
    vehicle_body_frontier_path: Path,
    component_callsite_path: Path,
) -> dict[str, Any]:
    outer = _load(outer_callsite_path, OUTER_FORMAT)
    frontier = _load(vehicle_body_frontier_path, VEHICLE_FRONTIER_FORMAT)
    callsite = _load(component_callsite_path, CALLSITE_FORMAT)

    source = outer.get("source") or {}
    ghidra = outer.get("ghidra") or {}
    outer_update = outer.get("outer_update") or {}
    _require(source.get("sha256") == SOURCE_SHA256, "outer source snapshot drift")
    _require(ghidra.get("executable_md5") == PE_MD5, "outer executable identity drift")
    _require(outer_update.get("function") == OUTER_UPDATE, "outer-update anchor drift")
    outer_symbol = outer_update.get("receiver_at_callsites")
    outer_address = _dat_symbol_address(outer_symbol)
    _require(outer_address == GLOBAL_VEHICLE_ADDRESS, "outer receiver address drift")

    _require(callsite.get("source_snapshot_sha256") == SOURCE_SHA256, "Phase 633 source identity drift")
    _require(callsite.get("executable_md5") == PE_MD5, "Phase 633 executable identity drift")
    runtime = callsite.get("runtime_component_callsite") or {}
    layout = callsite.get("vehicle_layout_join") or {}
    scope = callsite.get("scope") or {}
    _require(_int(runtime.get("call_address")) == RUNTIME_CALL, "runtime component call address drift")
    _require(_int(runtime.get("return_address")) == RUNTIME_RETURN, "runtime component return address drift")
    _require(runtime.get("caller_name") == RUNTIME_CALLER, "runtime component caller drift")
    _require(_int(runtime.get("callee_core")) == MUTATION_CORE, "relation mutation core drift")
    _require(runtime.get("vehicle_pointer_register_at_core_entry") == "ECX", "vehicle register ABI drift")
    _require(runtime.get("component_offset_register_at_core_entry") == "EAX", "component register ABI drift")
    vehicle_address = _int(runtime.get("vehicle_base_address"))
    _require(vehicle_address == GLOBAL_VEHICLE_ADDRESS, "global vehicle base address drift")
    _require(_int(runtime.get("component_base_offset")) == 0x400, "component base drift")
    _require(_int(runtime.get("component_stride")) == 0xA80, "component stride drift")
    _require(_int(runtime.get("component_count")) == 4, "component count drift")
    _require(layout.get("solver_setup_function") == SOLVER_SETUP, "vehicle solver setup anchor drift")
    _require(layout.get("component_fields_same_layout_proven") is True, "solver/component layout join missing")
    _require(scope.get("global_vehicle_component_base_address_proven") is True, "global vehicle base not proven")
    _require(scope.get("update_child_pointer_equals_global_vehicle_base_proven") is False, "callsite evidence preclaims update-child equality")
    _require(scope.get("body_array_owner_equals_global_vehicle_base_proven") is False, "callsite evidence preclaims BODY owner equality")

    probe = _probe_module()
    probe_callsite = probe.RELATION_STATE_MUTATION_CALLSITES.get(RUNTIME_RETURN)
    _require(isinstance(probe_callsite, dict), "Phase 636 runtime callsite missing from probe contract")
    _require(int(probe_callsite.get("call_address")) == RUNTIME_CALL, "Phase 636 call address mismatch")
    _require(probe_callsite.get("source_function") == RUNTIME_CALLER, "Phase 636 caller mismatch")
    _require(probe_callsite.get("kind") == "runtime-threshold-slot", "Phase 636 caller class mismatch")
    probe_layout = probe.RELATION_STATE_MUTATION_LAYOUT
    _require(probe_layout.get("component_base_offset") == 0x400, "probe component base drift")
    _require(probe_layout.get("component_stride") == 0xA80, "probe component stride drift")
    _require(probe_layout.get("component_count") == 4, "probe component count drift")
    _require(probe.FUNCTIONS.get("relation_state_mutation") == MUTATION_CORE, "probe mutation core drift")

    domains = frontier.get("pointer_domains") or {}
    frontier_scope = frontier.get("scope") or {}
    update_child = domains.get("update_child_receiver") or {}
    outer_domain = domains.get("outer_physics_receiver") or {}
    _require(update_child.get("source_rule") == "*record + 0x340", "update-child source rule drift")
    _require(_dat_symbol_address(outer_domain.get("source_expression")) == GLOBAL_VEHICLE_ADDRESS, "frontier outer receiver drift")
    _require(frontier_scope.get("normal_outer_call_forwards_vehicle_receiver_pointer") is False, "frontier unexpectedly forwards update-child pointer")
    _require(frontier_scope.get("outer_receiver_to_BODY_owner_pointer_continuity_proven") is False, "BODY owner continuity unexpectedly pre-proven")

    return {
        "format": FORMAT,
        "inputs": {
            "outer_update_callsite": str(outer_callsite_path),
            "vehicle_body_identity_frontier": str(vehicle_body_frontier_path),
            "phase633_global_vehicle_callsite": str(component_callsite_path),
        },
        "identity_join": {
            "outer_update_receiver_symbol": str(outer_symbol),
            "outer_update_receiver_address": f"0x{outer_address:08x}",
            "runtime_component_vehicle_base_address": f"0x{vehicle_address:08x}",
            "same_numeric_address": outer_address == vehicle_address,
            "evidence_state": "proven-composed-static",
            "global_outer_receiver_is_vehicle_component_base": True,
            "vehicle_component_entry_abi": "ECX=vehicle, EAX=slot*0xa80",
            "runtime_component_call_address": f"0x{RUNTIME_CALL:08x}",
            "runtime_component_caller": RUNTIME_CALLER,
            "solver_setup_layout_anchor": SOLVER_SETUP,
        },
        "update_child_role": {
            "source_rule": "*record + 0x340",
            "pointer_forwarded_to_outer_update": False,
            "pointer_identity_with_global_vehicle_base": "unknown",
            "pointer_identity_required_to_prove_global_vehicle_base": False,
            "evidence_state": "separate-pointer-domain",
        },
        "remaining_blockers": [
            {
                "id": "global-vehicle-base-to-BODY-array-owner-continuity",
                "evidence_state": "unknown",
                "targets": [HALF_STEP, BODY_ARRAY_LOOP],
                "required_evidence": (
                    "prove exact receiver/pointer provenance from the DAT_00c13700 outer-update "
                    "domain through FUN_00765470 to the FUN_007b2270 BODY-array owner"
                ),
            },
            {
                "id": "BODY-pose-to-renderer-world-transform-convention",
                "evidence_state": "blocked",
                "blocked_by": "global-vehicle-base-to-BODY-array-owner-continuity",
            },
        ],
        "next_instruction_targets": [HALF_STEP, BODY_ARRAY_LOOP],
        "handoff": {
            "global_vehicle_component_base_identity_ready": True,
            "global_vehicle_address": f"0x{GLOBAL_VEHICLE_ADDRESS:08x}",
            "update_child_to_vehicle_base_equality_required": False,
            "update_child_to_vehicle_base_equality_proven": False,
            "outer_receiver_to_BODY_owner_continuity_proven": False,
            "vehicle_BODY_selection_ready": False,
            "vehicle_world_transform_ready": False,
            "phase698_positive_selection_admissible": False,
            "critical_next_join": "DAT_00c13700/FUN_00765470 -> FUN_007b2270 BODY-array owner receiver continuity",
        },
        "scope": {
            "same_address_plus_independent_vehicle_semantics_used": True,
            "matching_offsets_alone_used_as_identity": False,
            "update_child_relabelled_as_vehicle": False,
            "FUN_007615c0_runtime_receiver_equals_global_base_proven": False,
            "BODY_array_owner_equals_global_vehicle_base_proven": False,
            "runtime_event_timing_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outer_update_callsite", type=Path)
    parser.add_argument("vehicle_body_identity_frontier", type=Path)
    parser.add_argument("phase633_global_vehicle_callsite", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()
    report = build_global_vehicle_component_base_identity(
        args.outer_update_callsite,
        args.vehicle_body_identity_frontier,
        args.phase633_global_vehicle_callsite,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text("".join(f"{target}\n" for target in report["next_instruction_targets"]), encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"global vehicle base: {report['handoff']['global_vehicle_address']}")
    print(f"global vehicle identity ready: {report['handoff']['global_vehicle_component_base_identity_ready']}")
    print(f"vehicle BODY selection ready: {report['handoff']['vehicle_BODY_selection_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

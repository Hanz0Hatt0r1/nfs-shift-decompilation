#!/usr/bin/env python3
"""Trace the retail vehicle-init receiver into the SDF BODY loader.

The BODY0 construction proof already establishes:

    SDF BODY pos/ori -> FUN_007b6900 -> persistent BODY origin/basis

but deliberately stops at the SDF-model construction frame.  This analyzer
narrows the remaining frame join by proving only the physical IA-32 receiver
continuity on the retail vehicle initialization path:

    MWL::Core::HighDetailVehicle::Init (FUN_0076df50)
        --ECX at 0x0076e238--> FUN_007615c0
        --ECX at 0x007615ed--> FUN_007b6900

It consumes the ordinary saved Ghidra evidence database plus a targeted
``SHIFT.GhidraFunctionInstructions/2`` export for FUN_0076df50 and
FUN_007615c0.  The finite all-path register provenance engine is reused from
the already-regressed FUN_00765470 receiver proof.

A positive result proves pointer/receiver continuity only.  It does *not* infer
that the HighDetailVehicle object frame equals the VHF vehicle-root frame, that
BODY0 local equals the body-MEB local frame, or that the BODY0 bind matrix is
identity.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_callsite_register_provenance as _callsite_engine

FORMAT = "SHIFT.BMWSDFVehicleAssemblyReceiverProvenance/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
INIT_LABEL = "MWL::Core::HighDetailVehicle::Init"
RECEIVER_REGISTER = "ECX"

TARGETS: dict[str, dict[str, str]] = {
    "0x0076df50": {
        "name": "FUN_0076df50",
        "mnemonic_sha256": "73a0d9d46d5d1bfd58068d2f72e91b77cf8c31cadb27745ba75b646901834dda",
        "calling_convention": "__thiscall",
        "role": "HighDetailVehicle Init source-anchor function",
    },
    "0x007615c0": {
        "name": "FUN_007615c0",
        "mnemonic_sha256": "0b2268dceb26dfaff8814b4091e50d48371b74083ac6d41e3d50da99cc036a22",
        "calling_convention": "__thiscall",
        "role": "vehicle physics assembly / named BODY consumer",
    },
    "0x007b6900": {
        "name": "FUN_007b6900",
        "mnemonic_sha256": "154593816d7647c6cd8a0ee37b96e92c38cd78b318bd16cdbfcefb7bca3aba81",
        "calling_convention": "__thiscall",
        "role": "SDF BODY loader",
    },
}

CALLS = (
    {
        "caller": "0x0076df50",
        "callsite": "0x0076e238",
        "callee": "0x007615c0",
        "id": "high-detail-vehicle-init-to-physics-assembly",
    },
    {
        "caller": "0x007615c0",
        "callsite": "0x007615ed",
        "callee": "0x007b6900",
        "id": "physics-assembly-to-sdf-loader",
    },
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _address(value: Any, *, field: str) -> str:
    try:
        return _callsite_engine._address(value, field=field)
    except ValueError as exc:
        raise ValueError(f"{field}: {exc}") from exc


def _sorted_origins(values: Iterable[str]) -> list[str]:
    return sorted(set(str(value) for value in values))


def _validate_retail_export(root: Path) -> dict[str, Any]:
    binary_path = root / "binary.json"
    functions_path = root / "functions.jsonl"
    callgraph_path = root / "callgraph.jsonl"
    strings_path = root / "strings_xrefs.jsonl"
    for path in (binary_path, functions_path, callgraph_path, strings_path):
        if not path.is_file():
            raise ValueError(f"missing Ghidra evidence file: {path}")

    binary = _load_json(binary_path)
    if binary.get("program_name") != PROGRAM:
        raise ValueError(f"unexpected Ghidra program: {binary.get('program_name')!r}")
    if binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable MD5")

    found: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(functions_path):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _address(raw, field="functions.address")
        if address not in TARGETS:
            continue
        if address in found:
            raise ValueError(f"duplicate function row {address}")
        found[address] = row

    missing = sorted(set(TARGETS) - set(found))
    if missing:
        raise ValueError("missing required retail function(s): " + ", ".join(missing))
    for address, expected in TARGETS.items():
        row = found[address]
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        if row.get("name") != expected["name"]:
            raise ValueError(f"{address}: function name drift")
        if row.get("mnemonic_sha256") != expected["mnemonic_sha256"]:
            raise ValueError(f"{address}: mnemonic fingerprint drift")
        if row.get("calling_convention") != expected["calling_convention"]:
            raise ValueError(f"{address}: calling convention drift")

    edges: set[tuple[str, str, str]] = set()
    for row in _read_jsonl(callgraph_path):
        if row.get("indirect") is True:
            continue
        raw_from = row.get("from_function")
        raw_instruction = row.get("instruction")
        raw_to = row.get("to")
        if not all(isinstance(value, str) for value in (raw_from, raw_instruction, raw_to)):
            continue
        edges.add(
            (
                _address(raw_from, field="callgraph.from_function"),
                _address(raw_instruction, field="callgraph.instruction"),
                _address(raw_to, field="callgraph.to"),
            )
        )
    missing_edges = [
        (row["caller"], row["callsite"], row["callee"])
        for row in CALLS
        if (row["caller"], row["callsite"], row["callee"]) not in edges
    ]
    if missing_edges:
        raise ValueError(
            "missing required direct call edge(s): "
            + ", ".join(f"{a}:{i}->{b}" for a, i, b in missing_edges)
        )

    label_rows: list[dict[str, Any]] = []
    for row in _read_jsonl(strings_path):
        if row.get("value") != INIT_LABEL:
            continue
        raw_functions = row.get("functions")
        if not isinstance(raw_functions, list):
            continue
        functions: list[str] = []
        for raw in raw_functions:
            if not isinstance(raw, str):
                continue
            try:
                functions.append(_address(raw, field="strings_xrefs.functions"))
            except ValueError:
                continue
        label_rows.append(
            {
                "address": row.get("address"),
                "xrefs": list(row.get("xrefs") or []),
                "functions": functions,
            }
        )
    init_address = "0x0076df50"
    if not any(init_address in row["functions"] for row in label_rows):
        raise ValueError(
            "HighDetailVehicle::Init source/debug label is not anchored to FUN_0076df50"
        )

    return {
        "program_name": PROGRAM,
        "executable_md5": PE_MD5,
        "functions": [
            {
                "address": address,
                "name": TARGETS[address]["name"],
                "role": TARGETS[address]["role"],
                "calling_convention": TARGETS[address]["calling_convention"],
                "mnemonic_sha256": TARGETS[address]["mnemonic_sha256"],
            }
            for address in TARGETS
        ],
        "required_direct_edges": [dict(row) for row in CALLS],
        "high_detail_vehicle_init_label": {
            "value": INIT_LABEL,
            "function": init_address,
            "observed": True,
            "rows": label_rows,
        },
    }


def _call_target(instruction: Mapping[str, Any], target: str) -> bool:
    normalized: list[str] = []
    flows = instruction.get("flows")
    if isinstance(flows, list):
        for value in flows:
            if not isinstance(value, str):
                continue
            try:
                normalized.append(_address(value, field="call flow"))
            except ValueError:
                pass
    if target in normalized:
        return True
    operands = instruction.get("operands")
    if isinstance(operands, list):
        for value in operands:
            if not isinstance(value, str):
                continue
            try:
                if _address(value, field="call operand") == target:
                    return True
            except ValueError:
                continue
    return False


def _classify_origins(origins: list[str]) -> str:
    if origins == [f"entry:{RECEIVER_REGISTER}"]:
        return "exact-entry-receiver"
    flags = _callsite_engine._origin_flags(origins)
    if flags["origin_count"] != 1 or flags["contains_unknown_or_derived"]:
        return "ambiguous"
    if flags["contains_memory_origin"]:
        return "memory-derived-nonidentity"
    return "verified-nonentry-origin"


def _analyze_call(
    instructions: list[dict[str, Any]],
    *,
    caller: str,
    callsite: str,
    callee: str,
    link_id: str,
) -> dict[str, Any]:
    by_address = {
        _address(instruction.get("address"), field="instruction.address"): instruction
        for instruction in instructions
    }
    call = by_address.get(callsite)
    if call is None:
        raise ValueError(f"{caller}: missing required callsite {callsite}")
    if str(call.get("mnemonic") or "").upper() != "CALL":
        raise ValueError(f"{caller}:{callsite}: required instruction is not CALL")
    if not _call_target(call, callee):
        raise ValueError(f"{caller}:{callsite}: expected direct target {callee}")

    incoming, iterations = _callsite_engine._analyze_incoming_states(instructions)
    state = incoming.get(callsite)
    if state is None:
        raise ValueError(f"{caller}:{callsite}: callsite is unreachable from function entry")
    origins = _sorted_origins(state[RECEIVER_REGISTER])
    exact = origins == [f"entry:{RECEIVER_REGISTER}"]
    return {
        "id": link_id,
        "caller": caller,
        "callsite": callsite,
        "callee": callee,
        "callee_calling_convention": "__thiscall",
        "physical_receiver_register": RECEIVER_REGISTER,
        "receiver_origins_before_call": origins,
        "receiver_origin_cardinality": len(origins),
        "receiver_equals_caller_entry_ECX_on_all_reachable_paths": exact,
        "classification": _classify_origins(origins),
        "fixed_point_iterations": iterations,
        "reachable_instruction_count": len(incoming),
        "function_instruction_count": len(instructions),
        "lexical_window": _callsite_engine._lexical_window(instructions, callsite),
    }


def analyze_bmw_sdf_vehicle_assembly_receiver_provenance(
    ghidra_export: Path,
    instruction_export: Path,
) -> dict[str, Any]:
    retail = _validate_retail_export(ghidra_export)
    instruction_rows = _callsite_engine._index_instruction_rows(instruction_export)
    required_instruction_functions = ("0x0076df50", "0x007615c0")
    missing = [
        address for address in required_instruction_functions
        if address not in instruction_rows
    ]
    if missing:
        raise ValueError(
            "instruction export missing required function(s): " + ", ".join(missing)
        )

    links = [
        _analyze_call(
            instruction_rows[row["caller"]],
            caller=row["caller"],
            callsite=row["callsite"],
            callee=row["callee"],
            link_id=row["id"],
        )
        for row in CALLS
    ]
    chain_ready = all(
        row["receiver_equals_caller_entry_ECX_on_all_reachable_paths"] is True
        for row in links
    )

    blocking_reasons: list[dict[str, Any]] = []
    for row in links:
        if row["receiver_equals_caller_entry_ECX_on_all_reachable_paths"] is True:
            continue
        blocking_reasons.append(
            {
                "id": row["id"] + "-ECX-continuity-unproven",
                "evidence_state": (
                    "ambiguous"
                    if row["classification"] == "ambiguous"
                    else "verified-nonidentity"
                ),
                "caller": row["caller"],
                "callsite": row["callsite"],
                "callee": row["callee"],
                "observed_origins": row["receiver_origins_before_call"],
                "required_evidence": (
                    "resolve every reachable ECX producer at the direct callsite "
                    "to the caller entry ECX value"
                ),
            }
        )

    remaining_frame_blockers = [
        {
            "id": "high-detail-vehicle-receiver-to-vhf-root-frame-semantic-binding-unproven",
            "evidence_state": "unknown",
            "required_relation": "HighDetailVehicle assembly owner frame -> VHF vehicle-root frame",
            "required_evidence": (
                "static/source-backed assembly transform ownership; pointer equality or "
                "the HighDetailVehicle::Init debug label alone is not frame identity"
            ),
        },
        {
            "id": "BODY0-resource-pos-ori-values-unavailable",
            "evidence_state": "data-unavailable",
            "required_resource": "vehicles/physics/suspension/aarm_multilink.sdf",
            "required_decoded_sha256": (
                "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
            ),
        },
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if chain_ready else "blocked",
        "ready": chain_ready,
        "inputs": {
            "ghidra_export": str(ghidra_export),
            "instruction_export": str(instruction_export),
            "instruction_format": INSTRUCTION_FORMAT,
        },
        "retail_identity": retail,
        "receiver_links": links,
        "analysis": {
            "high_detail_vehicle_init_to_physics_assembly_receiver_continuity_proven": (
                links[0]["receiver_equals_caller_entry_ECX_on_all_reachable_paths"]
            ),
            "physics_assembly_to_sdf_loader_receiver_continuity_proven": (
                links[1]["receiver_equals_caller_entry_ECX_on_all_reachable_paths"]
            ),
            "high_detail_vehicle_init_to_sdf_loader_receiver_continuity_proven": chain_ready,
            "physical_receiver_chain": (
                "FUN_0076df50 entry ECX == FUN_007615c0 entry ECX == "
                "FUN_007b6900 entry ECX"
                if chain_ready
                else None
            ),
        },
        "handoff": {
            "SDF_loader_owner_receiver_continuity_ready": chain_ready,
            "SDF_loader_receiver_equals_HighDetailVehicle_Init_entry_ECX": chain_ready,
            "SDF_model_to_VHF_vehicle_root_frame_relation_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "next_required_proof": (
                "HighDetailVehicle assembly owner frame -> VHF vehicle-root frame semantic relation"
                if chain_ready
                else "exact ECX receiver continuity at the blocked direct callsite(s)"
            ),
        },
        "blocking_reasons": blocking_reasons,
        "remaining_frame_blockers": remaining_frame_blockers,
        "scope": {
            "physical_receiver_provenance_only": True,
            "debug_method_label_observed": True,
            "debug_method_label_is_frame_identity": False,
            "receiver_pointer_identity_is_frame_identity": False,
            "HighDetailVehicle_this_equals_VHF_root_frame_assumed": False,
            "SDF_model_frame_equals_VHF_root_frame_assumed": False,
            "BODY0_local_equals_MEB_local_assumed": False,
            "BODY0_bind_matrix_identity_assumed": False,
            "BODY0_bind_matrix_emitted": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_bmw_sdf_vehicle_assembly_receiver_provenance(
        args.ghidra_export,
        args.instruction_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

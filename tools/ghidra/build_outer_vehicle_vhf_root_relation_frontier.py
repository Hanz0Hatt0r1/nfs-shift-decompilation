#!/usr/bin/env python3
"""Bound the remaining outer-Vehicle-root -> VHF-root static proof neighborhood.

``SHIFT.BMWBody0VehicleRootBindRelation/1`` already proves BODY0-local -> outer
Vehicle-root symbolically. ``SHIFT.BMWVHFBodyWorldTransform/1`` independently
provides the canonical BMW VHF hierarchy/body-MEB assembly transform.  The one
remaining frame-identity question is whether the retail outer Vehicle root set
at spawn is the VHF hierarchy vehicle root, or whether an additional fixed
affine relation exists between them.

This builder does not answer that semantic question by callgraph adjacency.  It
freezes the exact source-labelled spawn path and the finite direct-call fan-out
of the retail outer Vehicle transform setter, then emits the smallest targeted
instruction worklist needed for a later receiver/argument/store proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.OuterVehicleVHFRootRelationFrontier/1"
SYMBOLIC_FORMAT = "SHIFT.BMWBody0VehicleRootBindRelation/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

RESTART = "0x0074ddc3"
OUTER_SETTER = "0x007927c0"
HDVEHICLE_SETTER = "0x007633b0"

TARGETS: dict[str, dict[str, Any]] = {
    "0x0074ddc3": {
        "name": "FUN_0074ddc3",
        "size": 957,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "1b8f7a6602190fdd97b5a3d410495c8ff92b3a8b854a703459427b1ff548e4a6",
        "role": "source-labelled PhysicsParticipant::Restart spawn owner",
    },
    "0x007927c0": {
        "name": "FUN_007927c0",
        "size": 340,
        "calling_convention": "__thiscall",
        "mnemonic_sha256": "32b16c7d280c26335f9244b4cc7f8269995e4d2608724f8b0e5c4c0c41a75561",
        "role": "source-backed outer Vehicle transform setter",
    },
    "0x007af6e0": {
        "name": "FUN_007af6e0",
        "size": 257,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "13dcda957d9c318f066755dd7b1154042e1709693425e92fb547a025827fd8e3",
        "role": "fastcall no-this helper candidate",
    },
    "0x007876e0": {
        "name": "FUN_007876e0",
        "size": 70,
        "calling_convention": "__thiscall",
        "mnemonic_sha256": "6dd7d4522a98ffc6eb0bdb39a5f2fde5869579297f12342ce199e9ffbb1ffa48",
        "role": "thiscall transform/state sink candidate",
    },
    "0x007afb60": {
        "name": "FUN_007afb60",
        "size": 49,
        "calling_convention": "__thiscall",
        "mnemonic_sha256": "93c1afd52632f79c7019e6533ea7049ccf83717f589e521fabe0cfb433cbf12f",
        "role": "thiscall vector-triplet sink candidate",
    },
    "0x004a7870": {
        "name": "FUN_004a7870",
        "size": 36,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "fda8fcb2b4d9c692033d047f34517b0b63f7f13bbcc9d63f59b57d3f6719b2cd",
        "role": "fastcall three-vector helper candidate",
    },
    "0x00787160": {
        "name": "FUN_00787160",
        "size": 149,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "754b8c35ce6b742a7c7e5574ea3c80041f87d6256aef71db9a30e08d06a5d79d",
        "role": "fastcall state/transform helper candidate",
    },
    "0x007633b0": {
        "name": "FUN_007633b0",
        "size": 319,
        "calling_convention": "__thiscall",
        "mnemonic_sha256": "34643530b03a2868818cec0b31ed9f0f03ca146df2c1e915e846b88033aaebfe",
        "role": "already-proven HDVehicle chassis transform sink",
    },
    "0x007ac2f0": {
        "name": "FUN_007ac2f0",
        "size": 279,
        "calling_convention": "__thiscall",
        "mnemonic_sha256": "01f0b0a953c9f3dedc501d659b4a5cc952d3a4330eef92f154e3ad9ace85c7ba",
        "role": "thiscall post-transform state sink candidate",
    },
}

RESTART_LABELS = (
    {
        "address": "0x00b086a4",
        "value": ".\\Source\\System\\PhysicsParticipant.cpp",
        "xref": "0x0074e048",
    },
    {
        "address": "0x00b086cc",
        "value": "MWL::Core::PhysicsParticipant::Restart",
        "xref": "0x0074e041",
    },
    {
        "address": "0x00b086f8",
        "value": "Car %d tried to spawn at 0,0,0 - was attempting to spawn to grid spot %d",
        "xref": "0x0074e032",
    },
)

# Restart has multiple branch-specific spawn paths.  All direct calls to the
# source-backed outer Vehicle setter are frozen, rather than selecting one branch.
RESTART_TO_OUTER_CALLS = (
    "0x0074de8c",
    "0x0074df26",
    "0x0074df62",
    "0x0074dfce",
)

OUTER_SETTER_CALLS = (
    ("0x007927fd", "0x007af6e0"),
    ("0x0079280e", "0x007876e0"),
    ("0x00792828", "0x007afb60"),
    ("0x00792837", "0x004a7870"),
    ("0x00792884", "0x00787160"),
    ("0x007928e3", "0x007633b0"),
    ("0x007928f0", "0x007ac2f0"),
)

# The initial instruction proof can ignore the two no-this helpers.  Their exact
# semantics are relevant only if the outer-setter value slice terminates there.
TARGETED_INSTRUCTION_WORKLIST = (
    "FUN_0074ddc3",
    "FUN_007927c0",
    "FUN_007876e0",
    "FUN_007afb60",
    "FUN_00787160",
    "FUN_007633b0",
    "FUN_007ac2f0",
)


def _load(path: Path) -> dict[str, Any]:
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
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(value)
    return rows


def _addr(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}: expected address string")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"{field}: invalid address {value!r}") from exc


def _validate_symbolic_relation(path: Path) -> dict[str, Any]:
    report = _load(path)
    if report.get("format") != SYMBOLIC_FORMAT:
        raise ValueError(f"{path}: expected {SYMBOLIC_FORMAT}")
    if report.get("ready") is not True or report.get("status") != "symbolic-ready":
        raise ValueError("BODY0 -> outer Vehicle symbolic relation is not ready")
    gates = report.get("gates")
    if not isinstance(gates, Mapping):
        raise ValueError("symbolic relation gates missing")
    if gates.get("retail_vehicle_transform_to_HDVehicle_spawn_bridge_ready") is not True:
        raise ValueError("outer Vehicle -> HDVehicle spawn bridge is not ready")
    if gates.get("BODY0_to_outer_vehicle_root_symbolic_matrix_ready") is not True:
        raise ValueError("BODY0 -> outer Vehicle symbolic matrix is not ready")
    if gates.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise ValueError("symbolic relation unexpectedly preclaims outer Vehicle -> VHF root")
    if gates.get("BODY0_bind_frame_proof_ready") is not False:
        raise ValueError("symbolic relation unexpectedly preclaims BODY0 bind proof")
    scope = report.get("scope")
    if not isinstance(scope, Mapping) or scope.get("outer_vehicle_root_equated_to_VHF_root") is not False:
        raise ValueError("symbolic relation scope no longer fails closed on VHF root identity")
    retail = report.get("retail")
    functions = retail.get("functions") if isinstance(retail, Mapping) else None
    if not isinstance(functions, list):
        raise ValueError("symbolic relation retail function inventory missing")
    hit = next(
        (
            row for row in functions
            if isinstance(row, Mapping)
            and str(row.get("address") or "").lower() == OUTER_SETTER
        ),
        None,
    )
    expected = TARGETS[OUTER_SETTER]
    if not isinstance(hit, Mapping) or hit.get("mnemonic_sha256") != expected["mnemonic_sha256"]:
        raise ValueError("symbolic relation outer Vehicle setter anchor drift")
    return report


def _validate_retail(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    binary = _load(root / "binary.json")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")

    found: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(root / "functions.jsonl"):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _addr(raw, "functions.address")
        if address in TARGETS:
            if address in found:
                raise ValueError(f"duplicate function row {address}")
            found[address] = row

    missing = sorted(set(TARGETS) - set(found))
    if missing:
        raise ValueError("missing required retail function(s): " + ", ".join(missing))

    functions: list[dict[str, Any]] = []
    for address, expected in TARGETS.items():
        row = found[address]
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        for key in ("name", "size", "calling_convention", "mnemonic_sha256"):
            if row.get(key) != expected[key]:
                raise ValueError(f"{address}: {key} drift")
        functions.append({
            "address": address,
            "name": expected["name"],
            "size": expected["size"],
            "calling_convention": expected["calling_convention"],
            "mnemonic_sha256": expected["mnemonic_sha256"],
            "role": expected["role"],
        })

    edges: set[tuple[str, str, str]] = set()
    direct_from_outer: list[tuple[str, str]] = []
    direct_restart_to_outer: list[str] = []
    for row in _read_jsonl(root / "callgraph.jsonl"):
        if row.get("indirect") is True:
            continue
        raw_from, raw_insn, raw_to = row.get("from_function"), row.get("instruction"), row.get("to")
        if not all(isinstance(value, str) for value in (raw_from, raw_insn, raw_to)):
            continue
        source = _addr(raw_from, "callgraph.from_function")
        instruction = _addr(raw_insn, "callgraph.instruction")
        target = _addr(raw_to, "callgraph.to")
        edges.add((source, instruction, target))
        if source == OUTER_SETTER:
            direct_from_outer.append((instruction, target))
        if source == RESTART and target == OUTER_SETTER:
            direct_restart_to_outer.append(instruction)

    expected_restart = set(RESTART_TO_OUTER_CALLS)
    observed_restart = set(direct_restart_to_outer)
    if observed_restart != expected_restart:
        missing_calls = sorted(expected_restart - observed_restart)
        extra_calls = sorted(observed_restart - expected_restart)
        raise ValueError(
            "PhysicsParticipant::Restart -> outer setter callsite drift; "
            f"missing={missing_calls}, extra={extra_calls}"
        )

    expected_outer = set(OUTER_SETTER_CALLS)
    observed_outer = set(direct_from_outer)
    if observed_outer != expected_outer:
        missing_calls = sorted(expected_outer - observed_outer)
        extra_calls = sorted(observed_outer - expected_outer)
        raise ValueError(
            "outer Vehicle setter direct-call fan-out drift; "
            f"missing={missing_calls}, extra={extra_calls}"
        )

    labels_by_address: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(root / "strings_xrefs.jsonl"):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        labels_by_address[_addr(raw, "strings.address")] = row

    labels: list[dict[str, str]] = []
    for expected in RESTART_LABELS:
        row = labels_by_address.get(expected["address"])
        if not isinstance(row, Mapping):
            raise ValueError(f"missing Restart source label {expected['address']}")
        if row.get("value") != expected["value"]:
            raise ValueError(f"Restart source label text drift at {expected['address']}")
        xrefs = {
            _addr(value, "strings.xref")
            for value in row.get("xrefs") or []
            if isinstance(value, str)
        }
        functions_for_string = {
            _addr(value, "strings.function")
            for value in row.get("functions") or []
            if isinstance(value, str)
        }
        if expected["xref"] not in xrefs or RESTART not in functions_for_string:
            raise ValueError(f"Restart source label xref/function drift at {expected['address']}")
        labels.append(dict(expected))

    return functions, labels


def build_outer_vehicle_vhf_root_relation_frontier(
    ghidra_export: Path,
    symbolic_relation_path: Path,
) -> dict[str, Any]:
    relation = _validate_symbolic_relation(symbolic_relation_path)
    functions, labels = _validate_retail(ghidra_export)

    outer_calls = [
        {
            "instruction": instruction,
            "callee": callee,
            "callee_name": TARGETS[callee]["name"],
            "callee_role": TARGETS[callee]["role"],
            "semantic_transform_owner_proven": callee == HDVEHICLE_SETTER,
            "VHF_hierarchy_owner_proven": False,
        }
        for instruction, callee in OUTER_SETTER_CALLS
    ]

    candidate_sinks = [
        row for row in outer_calls
        if row["callee"] in {
            "0x007876e0",
            "0x007afb60",
            "0x00787160",
            "0x007ac2f0",
        }
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "status": "frontier-ready",
        "ready": True,
        "inputs": {
            "ghidra_export": str(ghidra_export),
            "symbolic_BODY0_to_outer_vehicle_relation": str(symbolic_relation_path),
        },
        "retail": {
            "program_name": PROGRAM,
            "executable_md5": PE_MD5,
            "functions": functions,
            "restart_source_labels": labels,
            "restart_to_outer_vehicle_setter_calls": [
                {"from": RESTART, "instruction": callsite, "to": OUTER_SETTER}
                for callsite in RESTART_TO_OUTER_CALLS
            ],
            "outer_vehicle_setter_direct_calls": outer_calls,
        },
        "proven": {
            "restart_function_source_identity": "MWL::Core::PhysicsParticipant::Restart",
            "spawn_path_reaches_outer_vehicle_transform_setter": True,
            "all_restart_to_outer_setter_direct_calls_frozen": True,
            "outer_vehicle_setter_direct_fanout_frozen": True,
            "outer_vehicle_setter_to_HDVehicle_spawn_bridge_ready": True,
            "BODY0_to_outer_vehicle_root_symbolic_matrix_ready": True,
        },
        "candidate_transform_state_sinks": candidate_sinks,
        "targeted_instruction_worklist": {
            "format": INSTRUCTION_FORMAT if False else "SHIFT.GhidraFunctionInstructions/2",
            "functions": list(TARGETED_INSTRUCTION_WORKLIST),
            "questions": [
                "At every Restart -> FUN_007927c0 callsite, prove the receiver and transform argument origins for each reachable spawn branch.",
                "Inside FUN_007927c0, prove which outgoing calls receive the same position/orientation values or deterministic derivatives.",
                "For each thiscall candidate sink, prove the receiver origin and concrete writes/forwards performed by the callee.",
                "Identify whether any proven sink receiver belongs to the same assembly/hierarchy owner that loads the canonical BMW VHF root; otherwise follow only the exact owner-producing edge.",
            ],
        },
        "handoff": {
            "outer_vehicle_spawn_path_static_frontier_ready": True,
            "outer_vehicle_transform_fanout_static_frontier_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": [
            {
                "id": "outer-vehicle-root-to-vhf-root-owner-valueflow-unproven",
                "required_evidence": (
                    "instruction-level receiver/argument/store continuity from source-labelled "
                    "Restart through FUN_007927c0 into a concrete assembly/hierarchy owner, then "
                    "join that owner to the canonical BMW VHF vehicle-root load path"
                ),
            }
        ],
        "scope": {
            "callgraph_adjacency_used_as_frame_identity": False,
            "thiscall_abi_used_as_owner_identity": False,
            "helper_names_used_as_transform_semantics": False,
            "outer_vehicle_root_equated_to_VHF_root": False,
            "identity_affine_delta_assumed": False,
            "VHF_body_MEB_local_frame_equated_to_vehicle_root": False,
            "new_runtime_capture_required": False,
            "original_game_executed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("symbolic_relation", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = build_outer_vehicle_vhf_root_relation_frontier(
        args.ghidra_export,
        args.symbolic_relation,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

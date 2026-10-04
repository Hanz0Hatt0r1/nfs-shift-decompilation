#!/usr/bin/env python3
"""Narrow the outer Vehicle-root/VHF join to concrete transform storage state.

This stage consumes the finite receiver-routing report for FUN_007927c0 and a
small targeted instruction export selected from that report.  It answers a
strictly physical question: which deterministic __thiscall sink(s) receive the
outer setter entry receiver directly, and what receiver-relative bytes or
forwarding calls do those functions mutate?

The analyzer deliberately does not infer VHF hierarchy identity from class-like
call patterns.  It also records that FUN_007ac2f0 is called from both the outer
Vehicle setter and the independently-proven HDVehicle setter, so that shared
post-transform edge is not treated as a unique VHF-owner signal.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_callsite_register_provenance as _callsite
import analyze_bmw_body0_bind_pose_writer_value_provenance as _values
import analyze_outer_vehicle_transform_sink_receiver_provenance as _receivers
import analyze_register_relative_accesses as _access
import build_outer_vehicle_vhf_root_relation_frontier as _frontier

FORMAT = "SHIFT.OuterVehicleTransformStorageDomain/1"
RECEIVER_FORMAT = _receivers.FORMAT
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = _frontier.PROGRAM
PE_MD5 = _frontier.PE_MD5
OUTER_SETTER = _frontier.OUTER_SETTER
HDVEHICLE_SETTER = _frontier.HDVEHICLE_SETTER
SHARED_POST_TRANSFORM = "0x007ac2f0"
TRIPLET_SINK = "0x007afb60"
TRIPLET_HELPER = "0x007aef50"
DIRECT_OUTER_CANDIDATES = tuple(
    row["callee"]
    for row in _receivers.SINK_CALLS
    if row["physical_ecx_role"] == "thiscall-receiver"
    and row["callee"] != HDVEHICLE_SETTER
)

EXTRA_TARGETS: dict[str, dict[str, Any]] = {
    TRIPLET_HELPER: {
        "name": "FUN_007aef50",
        "size": 83,
        "calling_convention": "__thiscall",
        "mnemonic_sha256": "4f20a5f630bb6182c44699f505011f5a1958a87f4433400b7776ffd1dc740c51",
        "role": "vector-pair helper reached from FUN_007afb60",
    },
}


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
    return _callsite._address(value, field=field)


def _validate_receiver_report(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report = _load_json(path)
    if report.get("format") != RECEIVER_FORMAT:
        raise ValueError(f"{path}: expected {RECEIVER_FORMAT}")
    if report.get("ready") is not True:
        raise ValueError("outer Vehicle sink receiver provenance is not ready")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("receiver provenance handoff missing")
    if handoff.get("outer_setter_sink_ECX_provenance_evaluated") is not True:
        raise ValueError("outer setter sink ECX provenance was not evaluated")
    for key in (
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "outer_vehicle_root_to_VHF_fixed_affine_delta_ready",
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
    ):
        if handoff.get(key) is not False:
            raise ValueError(f"receiver provenance unexpectedly preclaims {key}")

    raw = report.get("sink_receiver_analyses")
    if not isinstance(raw, list):
        raise ValueError("receiver provenance sink_receiver_analyses missing")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(raw):
        if not isinstance(row, Mapping):
            raise ValueError(f"sink_receiver_analyses[{index}] must be an object")
        callee = _address(row.get("callee"), field=f"sink_receiver_analyses[{index}].callee")
        if callee in seen:
            raise ValueError(f"duplicate receiver analysis for {callee}")
        seen.add(callee)
        rows.append({**row, "callee": callee})

    expected = {row["callee"] for row in _receivers.SINK_CALLS}
    if seen != expected:
        raise ValueError("receiver provenance sink set drift")
    return report, rows


def _retail_targets() -> dict[str, dict[str, Any]]:
    result = {
        address: dict(_frontier.TARGETS[address])
        for address in set(DIRECT_OUTER_CANDIDATES) | {HDVEHICLE_SETTER}
    }
    result.update(EXTRA_TARGETS)
    return result


def _validate_retail(ghidra_export: Path) -> dict[str, Any]:
    binary = _load_json(ghidra_export / "binary.json")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")

    targets = _retail_targets()
    found: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(ghidra_export / "functions.jsonl"):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _address(raw, field="functions.address")
        if address in targets:
            if address in found:
                raise ValueError(f"duplicate retail function row {address}")
            found[address] = row
    missing = sorted(set(targets) - set(found))
    if missing:
        raise ValueError("missing required retail function(s): " + ", ".join(missing))
    for address, expected in targets.items():
        row = found[address]
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        for key in ("name", "size", "calling_convention", "mnemonic_sha256"):
            if row.get(key) != expected[key]:
                raise ValueError(f"{address}: {key} drift")

    direct_edges: set[tuple[str, str, str]] = set()
    direct_from: dict[str, list[tuple[str, str]]] = {}
    for row in _read_jsonl(ghidra_export / "callgraph.jsonl"):
        if row.get("indirect") is True:
            continue
        raw_from, raw_insn, raw_to = row.get("from_function"), row.get("instruction"), row.get("to")
        if not all(isinstance(value, str) for value in (raw_from, raw_insn, raw_to)):
            continue
        source = _address(raw_from, field="callgraph.from_function")
        instruction = _address(raw_insn, field="callgraph.instruction")
        target = _address(raw_to, field="callgraph.to")
        direct_edges.add((source, instruction, target))
        direct_from.setdefault(source, []).append((instruction, target))

    required = {
        (OUTER_SETTER, "0x007928f0", SHARED_POST_TRANSFORM),
        (HDVEHICLE_SETTER, "0x007634df", SHARED_POST_TRANSFORM),
        (TRIPLET_SINK, "0x007afb6c", TRIPLET_HELPER),
    }
    missing_edges = sorted(required - direct_edges)
    if missing_edges:
        raise ValueError(f"required retail transform-domain call edge drift: {missing_edges}")

    return {
        "shared_post_transform_hook_called_from_outer_setter": True,
        "shared_post_transform_hook_called_from_HDVehicle_setter": True,
        "shared_post_transform_hook_is_unique_outer_owner_signal": False,
        "triplet_sink_to_helper_edge_ready": True,
        "direct_calls_from_candidate_functions": {
            address: [
                {"instruction": instruction, "callee": callee}
                for instruction, callee in sorted(direct_from.get(address, []))
            ]
            for address in (*DIRECT_OUTER_CANDIDATES, TRIPLET_HELPER)
        },
    }


def _direct_outer_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("physical_ecx_role") == "thiscall-receiver"
        and row.get("ECX_origin_deterministic") is True
        and row.get("ECX_equals_outer_setter_entry_ECX_on_all_reachable_paths") is True
        and row["callee"] != HDVEHICLE_SETTER
    ]


def _routing_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    control = next(row for row in rows if row["callee"] == HDVEHICLE_SETTER)
    direct_outer = _direct_outer_rows(rows)
    hd_expression_rows = [
        row for row in rows
        if row.get("physical_ecx_role") == "thiscall-receiver"
        and row["callee"] != HDVEHICLE_SETTER
        and row.get("same_ECX_origin_expression_set_as_HDVehicle_sink") is True
    ]
    other_rows = [
        row for row in rows
        if row.get("physical_ecx_role") == "thiscall-receiver"
        and row["callee"] != HDVEHICLE_SETTER
        and row not in direct_outer
        and row not in hd_expression_rows
    ]
    return {
        "HDVehicle_control": {
            "callee": HDVEHICLE_SETTER,
            "ECX_origins_before_call": control.get("ECX_origins_before_call"),
        },
        "direct_outer_receiver_candidates": [row["callee"] for row in direct_outer],
        "HDVehicle_origin_expression_candidates": [row["callee"] for row in hd_expression_rows],
        "other_thiscall_receiver_candidates": [row["callee"] for row in other_rows],
        "unique_direct_outer_receiver_candidate": (
            direct_outer[0]["callee"] if len(direct_outer) == 1 else None
        ),
        "unique_direct_outer_receiver_domain_ready": len(direct_outer) == 1,
        "matching_HDVehicle_origin_expression_promoted_to_pointer_equality": False,
    }


def _validate_instruction_rows(path: Path, required: set[str]) -> dict[str, list[dict[str, Any]]]:
    rows = _callsite._index_instruction_rows(path)
    missing = sorted(required - set(rows))
    if missing:
        raise ValueError("instruction export missing selected outer receiver sink(s): " + ", ".join(missing))
    extra = sorted(set(rows) - required)
    if extra:
        raise ValueError("instruction export contains unselected function(s): " + ", ".join(extra))
    return rows


def _store_ops(instruction: Mapping[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    pcode = instruction.get("pcode")
    if not isinstance(pcode, list):
        raise ValueError(f"{instruction.get('address')}: pcode missing")
    return [
        (index, operation)
        for index, operation in enumerate(pcode)
        if isinstance(operation, dict) and str(operation.get("opcode") or "").upper() == "STORE"
    ]


def _memory_operands(instruction: Mapping[str, Any]) -> list[tuple[int, str, tuple[str, int] | None]]:
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
        raise ValueError(f"{instruction.get('address')}: operands must be strings")
    result: list[tuple[int, str, tuple[str, int] | None]] = []
    for index, operand in enumerate(operands):
        if "[" not in operand and "]" not in operand:
            continue
        result.append((index, operand, _access._parse_memory_operand(operand)))
    return result


def _value_frontier(
    *,
    address: str,
    op_index: int,
    operation: Mapping[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, list[str]],
    bindings: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    inputs = operation.get("inputs")
    if not isinstance(inputs, list) or len(inputs) < 3:
        raise ValueError(f"{address}:{op_index}: STORE value input missing")
    value = _values._validate_varnode(inputs[2], context=f"{address}:{op_index}:STORE value")
    node_id = f"{address}:{op_index}"
    node_bindings = bindings.get(node_id)
    if not isinstance(node_bindings, list):
        raise ValueError(f"{node_id}: p-code input bindings missing")
    binding = next((row for row in node_bindings if row.get("input_index") == 2), None)
    if not isinstance(binding, Mapping):
        raise ValueError(f"{node_id}: STORE value binding missing")
    definition = binding.get("definition")
    slice_nodes, raw_roots = _values._slice_from_definition(
        definition if isinstance(definition, str) else None,
        value if definition is None else None,
        nodes,
        edges,
        bindings,
    )
    roots = [_values._classify_root(root) for root in raw_roots]
    return {
        "store_value_varnode": dict(value),
        "store_value_definition": definition,
        "value_dependency_slice": slice_nodes,
        "value_terminal_roots": roots,
        "value_terminal_root_kinds": sorted({str(root.get("root_kind")) for root in roots}),
        "value_semantic_join_required": any(root.get("semantic_join_required") is True for root in roots),
    }


def _analyze_selected_sink(function: str, instructions: list[dict[str, Any]]) -> dict[str, Any]:
    incoming, iterations = _callsite._analyze_incoming_states(instructions)
    nodes, edges, bindings = _values._structured_pcode_graph(instructions)
    stores: list[dict[str, Any]] = []
    structural_blockers: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []

    for instruction in instructions:
        address = _address(instruction.get("address"), field="instruction.address")
        if str(instruction.get("mnemonic") or "").upper() == "CALL":
            targets: list[str] = []
            for raw in list(instruction.get("flows") or []) + list(instruction.get("operands") or []):
                if not isinstance(raw, str):
                    continue
                try:
                    target = _address(raw, field="call target")
                except ValueError:
                    continue
                if target not in targets:
                    targets.append(target)
            calls.append({"instruction": address, "targets": targets, "text": instruction.get("text")})

        store_ops = _store_ops(instruction)
        if not store_ops:
            continue
        memory = _memory_operands(instruction)
        parsed = [row for row in memory if row[2] is not None]
        unparsed = [row for row in memory if row[2] is None]
        if len(store_ops) != 1 or len(parsed) != 1 or unparsed:
            structural_blockers.append(
                {
                    "instruction": address,
                    "reason": "STORE target cannot be uniquely joined to one simple register-relative operand",
                    "store_op_count": len(store_ops),
                    "memory_operands": [operand for _, operand, _ in memory],
                }
            )
            continue
        state = incoming.get(address)
        if state is None:
            structural_blockers.append({"instruction": address, "reason": "STORE unreachable in recovered CFG"})
            continue
        op_index, operation = store_ops[0]
        inputs = operation.get("inputs")
        if not isinstance(inputs, list) or len(inputs) < 3 or not isinstance(inputs[2], Mapping):
            raise ValueError(f"{address}:{op_index}: STORE value missing")
        width = inputs[2].get("size")
        if not isinstance(width, int) or width <= 0:
            raise ValueError(f"{address}:{op_index}: STORE width invalid")
        operand_index, operand, parsed_memory = parsed[0]
        assert parsed_memory is not None
        base_register, displacement = parsed_memory
        base_origins = (
            _callsite._register_engine._sorted_origins(state[base_register])
            if base_register in state else []
        )
        stores.append(
            {
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "operand_index": operand_index,
                "operand": operand,
                "base_register": base_register,
                "base_register_origins": base_origins,
                "displacement": displacement,
                "displacement_hex": f"0x{displacement:x}" if displacement >= 0 else f"-0x{-displacement:x}",
                "store_width": width,
                "receiver_relative_on_all_reachable_paths": base_origins == ["entry:ECX"],
                **_value_frontier(
                    address=address,
                    op_index=op_index,
                    operation=operation,
                    nodes=nodes,
                    edges=edges,
                    bindings=bindings,
                ),
            }
        )

    receiver_stores = [row for row in stores if row["receiver_relative_on_all_reachable_paths"] is True]
    receiver_bytes: set[int] = set()
    for row in receiver_stores:
        receiver_bytes.update(range(int(row["displacement"]), int(row["displacement"]) + int(row["store_width"])))
    return {
        "function": function,
        "function_name": _frontier.TARGETS[function]["name"],
        "instruction_count": len(instructions),
        "reachable_instruction_count": len(incoming),
        "fixed_point_iterations": iterations,
        "call_count": len(calls),
        "calls": calls,
        "store_count": len(stores),
        "receiver_relative_store_count": len(receiver_stores),
        "receiver_relative_stores": receiver_stores,
        "receiver_relative_bytes": sorted(receiver_bytes),
        "receiver_relative_field_spans": [
            {
                "offset": row["displacement"],
                "offset_hex": row["displacement_hex"],
                "size": row["store_width"],
            }
            for row in receiver_stores
        ],
        "other_simple_stores": [row for row in stores if row["receiver_relative_on_all_reachable_paths"] is False],
        "structural_blockers": structural_blockers,
        "receiver_storage_side_effect_ready": bool(receiver_stores) and not structural_blockers,
    }


def analyze_outer_vehicle_transform_storage_domain(
    ghidra_export: Path,
    receiver_report_path: Path,
    instruction_export: Path,
) -> dict[str, Any]:
    receiver_report, receiver_rows = _validate_receiver_report(receiver_report_path)
    retail = _validate_retail(ghidra_export)
    routing = _routing_summary(receiver_rows)
    direct_outer = set(routing["direct_outer_receiver_candidates"])

    instruction_rows = _validate_instruction_rows(instruction_export, direct_outer)
    sink_reports = [
        _analyze_selected_sink(function, instruction_rows[function])
        for function in sorted(direct_outer, key=lambda value: int(value, 0))
    ]
    structural_blockers = [
        {"function": row["function"], **blocker}
        for row in sink_reports
        for blocker in row["structural_blockers"]
    ]
    storage_ready = bool(sink_reports) and all(
        row["receiver_storage_side_effect_ready"] is True for row in sink_reports
    )
    unique_ready = routing["unique_direct_outer_receiver_domain_ready"] is True

    blockers: list[dict[str, Any]] = []
    if not direct_outer:
        blockers.append(
            {
                "id": "outer-setter-direct-receiver-sink-not-found",
                "required_evidence": "resolve the all-path ECX receiver provenance before selecting a transform storage sink",
            }
        )
    if len(direct_outer) > 1:
        blockers.append(
            {
                "id": "outer-setter-direct-receiver-domain-not-unique",
                "candidates": sorted(direct_outer),
                "required_evidence": "separate concrete side effects/owner roles for each direct outer-receiver sink",
            }
        )
    if structural_blockers:
        blockers.append(
            {
                "id": "outer-transform-storage-STORE-structure-ambiguous",
                "count": len(structural_blockers),
                "required_evidence": "resolve every ambiguous STORE target before promoting receiver fields",
            }
        )
    if sink_reports and not storage_ready:
        blockers.append(
            {
                "id": "outer-transform-receiver-storage-not-yet-proven",
                "required_evidence": "prove at least one all-path entry-ECX-relative STORE in every selected direct receiver sink",
            }
        )

    exact_fields = [
        {
            "function": report["function"],
            **span,
        }
        for report in sink_reports
        for span in report["receiver_relative_field_spans"]
    ]
    status = (
        "storage-domain-ready"
        if storage_ready and unique_ready
        else "storage-domain-frontier"
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": True,
        "inputs": {
            "ghidra_export": str(ghidra_export),
            "receiver_report": str(receiver_report_path),
            "instruction_export": str(instruction_export),
        },
        "routing": routing,
        "retail_topology": retail,
        "selected_outer_receiver_sinks": sink_reports,
        "exact_outer_receiver_field_spans": exact_fields,
        "structural_blockers": structural_blockers,
        "handoff": {
            "outer_vehicle_direct_receiver_domain_unique": unique_ready,
            "outer_vehicle_transform_storage_fields_ready": storage_ready,
            "outer_vehicle_transform_storage_domain_ready": storage_ready and unique_ready,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "next_proof": {
            "target": "exact outer Vehicle receiver transform field consumers -> canonical BMW VHF hierarchy vehicle-root owner",
            "receiver_field_spans": exact_fields,
            "shared_FUN_007ac2f0_is_unique_owner_target": False,
            "stack_position_orientation_provenance_required_only_after_storage_owner_join": True,
        },
        "scope": {
            "receiver_report_consumed_without_pointer_identity_promotion": True,
            "matching_HDVehicle_origin_expression_promoted_to_pointer_equality": False,
            "shared_callgraph_edge_promoted_to_class_identity": False,
            "shared_callgraph_edge_promoted_to_frame_identity": False,
            "receiver_relative_STORE_promoted_to_VHF_identity": False,
            "outer_vehicle_root_equated_to_VHF_root": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("receiver_report", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze_outer_vehicle_transform_storage_domain(
        args.ghidra_export,
        args.receiver_report,
        args.instruction_export,
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

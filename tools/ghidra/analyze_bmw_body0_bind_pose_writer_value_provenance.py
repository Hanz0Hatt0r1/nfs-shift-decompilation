#!/usr/bin/env python3
"""Build the exact value-provenance worklist for FUN_007b7840 pose writes.

This stage consumes a positive ``SHIFT.BMWBody0BindPoseWriterTargetRole/1`` and
the same targeted ``SHIFT.GhidraFunctionInstructions/2`` row.  For every
machine STORE already admitted as a persistent BODY origin/basis write it
separates the STORE value input from the address input and builds a structured
p-code backward dependency slice.

Instruction p-code is not SSA across control-flow joins, and x87/SSE return
register definitions are not invented across CALLs.  Consequently this report is
a finite static provenance frontier, not a bind-value proof.  It never marks the
bind matrix ready merely because a dependency slice exists.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_callsite_register_provenance as _callsite
import analyze_bmw_body0_bind_pose_writer_target_role as _target

FORMAT = "SHIFT.BMWBody0BindPoseWriterValueProvenance/1"
TARGET_ROLE_FORMAT = "SHIFT.BMWBody0BindPoseWriterTargetRole/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
POSE_WRITER = "0x007b7840"

_FLOATING_REGISTER = re.compile(r"^(?:ST[0-7]|XMM(?:[0-9]|1[0-5]))$", re.IGNORECASE)
_GENERAL_REGISTER = re.compile(
    r"^(?:EAX|EBX|ECX|EDX|ESI|EDI|EBP|ESP|AX|BX|CX|DX|SI|DI|BP|SP)$",
    re.IGNORECASE,
)


def _load_json(path: Path, expected_format: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict) or value.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
    return value


def _read_single_instruction_row(path: Path) -> dict[str, Any]:
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
    if len(rows) != 1:
        raise ValueError(f"{path}: expected one targeted instruction row; found {len(rows)}")
    return rows[0]


def _varnode_key(value: Any) -> tuple[str, str, int] | None:
    if not isinstance(value, dict):
        return None
    space = value.get("space")
    offset = value.get("offset")
    size = value.get("size")
    if not isinstance(space, str) or not isinstance(offset, str) or not isinstance(size, int):
        return None
    return (space.lower(), offset.lower(), size)


def _validate_varnode(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context}: structured varnode required")
    for key in ("text", "space", "offset"):
        if not isinstance(value.get(key), str):
            raise ValueError(f"{context}: varnode {key} missing")
    if not isinstance(value.get("size"), int) or value["size"] <= 0:
        raise ValueError(f"{context}: varnode size invalid")
    for key in ("constant", "register", "unique"):
        if not isinstance(value.get(key), bool):
            raise ValueError(f"{context}: varnode {key} flag missing")
    return value


def _validate_target_role(report: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    target = report.get("target")
    if not isinstance(target, dict) or _callsite._address(
        target.get("pose_writer"), field="target.pose_writer"
    ) != POSE_WRITER:
        raise ValueError("target-role pose-writer identity mismatch")

    handoff = report.get("handoff")
    if not isinstance(handoff, dict):
        raise ValueError("target-role handoff missing")
    if handoff.get("pose_writer_BODY_target_parameter_ready") is not True:
        raise ValueError("pose-writer BODY target parameter is not ready")
    parameter = handoff.get("pose_writer_BODY_target_parameter")
    if not isinstance(parameter, dict):
        raise ValueError("target-role parameter metadata missing")
    if parameter.get("semantic_role") != "persistent_BODY_pose_record_target" or parameter.get(
        "semantic_role_proven"
    ) is not True:
        raise ValueError("target-role parameter is not semantically proven as BODY pose target")
    if parameter.get("storage_kind") != "register":
        raise ValueError("target-role proof must identify a register-backed target parameter")
    ordinal = parameter.get("ordinal")
    if not isinstance(ordinal, int) or ordinal < 0:
        raise ValueError("target-role parameter ordinal invalid")

    for key in (
        "pose_writer_ABI_semantic_roles_ready",
        "BODY0_pointer_at_bind_callsite_ready",
        "BODY0_bind_origin_basis_values_ready",
        "BODY0_bind_frame_proof_ready",
    ):
        if handoff.get(key) is not False:
            raise ValueError(f"target-role report unexpectedly preclaims {key}")

    analysis = report.get("analysis")
    if not isinstance(analysis, dict):
        raise ValueError("target-role analysis missing")
    if analysis.get("unresolved_pose_writes") not in ([], None):
        raise ValueError("target-role report contains unresolved pose writes")
    witnesses = analysis.get("pose_write_witnesses")
    if not isinstance(witnesses, list) or not witnesses:
        raise ValueError("target-role pose write witnesses missing")

    covered: set[int] = set()
    normalized: list[dict[str, Any]] = []
    seen_instructions: set[str] = set()
    for index, witness in enumerate(witnesses):
        if not isinstance(witness, dict):
            raise ValueError(f"pose_write_witnesses[{index}] must be an object")
        address = _callsite._address(
            witness.get("instruction"), field=f"pose_write_witnesses[{index}].instruction"
        )
        if address in seen_instructions:
            raise ValueError(f"duplicate target-role pose write instruction {address}")
        seen_instructions.add(address)
        if witness.get("parameter_ordinal") != ordinal:
            raise ValueError(f"{address}: pose write witness target parameter drift")
        if witness.get("pcode_store_proven") is not True:
            raise ValueError(f"{address}: target-role witness lacks p-code STORE proof")
        store_width = witness.get("store_width")
        if not isinstance(store_width, int) or store_width <= 0:
            raise ValueError(f"{address}: target-role STORE width invalid")
        touched = witness.get("required_bytes_touched")
        if not isinstance(touched, list) or not touched or any(
            not isinstance(value, int) or value < 0 for value in touched
        ):
            raise ValueError(f"{address}: required_bytes_touched invalid")
        covered.update(touched)
        normalized.append({**witness, "instruction": address})

    required = set(_target._REQUIRED_BYTES)
    if covered != required:
        missing = sorted(required - covered)
        extra = sorted(covered - required)
        raise ValueError(
            "target-role witness coverage mismatch: "
            f"missing={missing} extra={extra}"
        )
    return dict(parameter), normalized


def _structured_pcode_graph(
    instructions: list[dict[str, Any]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[str]],
    dict[str, list[dict[str, Any]]],
]:
    """Build a conservative linear instruction-pcode def/use frontier.

    The graph intentionally records which input had a previous structured
    definition.  It does not manufacture PHI nodes across CFG joins; callers of
    this helper must therefore treat the result as a worklist, not all-path value
    identity proof.
    """

    last_def: dict[tuple[str, str, int], str] = {}
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, list[str]] = {}
    input_bindings: dict[str, list[dict[str, Any]]] = {}

    for instruction in instructions:
        address = _callsite._address(instruction.get("address"), field="instruction.address")
        pcode = instruction.get("pcode")
        if not isinstance(pcode, list):
            raise ValueError(f"{address}: pcode must be a list")
        for op_index, operation in enumerate(pcode):
            if not isinstance(operation, dict):
                raise ValueError(f"{address}:{op_index}: pcode operation must be an object")
            opcode = operation.get("opcode")
            text = operation.get("text")
            inputs = operation.get("inputs")
            output = operation.get("output")
            if not isinstance(opcode, str) or not opcode:
                raise ValueError(f"{address}:{op_index}: pcode opcode missing")
            if not isinstance(text, str):
                raise ValueError(f"{address}:{op_index}: pcode text missing")
            if not isinstance(inputs, list):
                raise ValueError(f"{address}:{op_index}: pcode inputs missing")
            if output is not None:
                _validate_varnode(output, context=f"{address}:{op_index}:output")

            node_id = f"{address}:{op_index}"
            bindings: list[dict[str, Any]] = []
            dependencies: list[str] = []
            for input_index, raw_input in enumerate(inputs):
                value = _validate_varnode(
                    raw_input, context=f"{address}:{op_index}:input[{input_index}]"
                )
                key = _varnode_key(value)
                dependency = None if key is None else last_def.get(key)
                if dependency is not None and dependency not in dependencies:
                    dependencies.append(dependency)
                bindings.append(
                    {
                        "input_index": input_index,
                        "varnode": dict(value),
                        "definition": dependency,
                    }
                )

            nodes[node_id] = {
                "id": node_id,
                "instruction": address,
                "opcode": opcode.upper(),
                "text": text,
                "output": output,
                "inputs": [dict(value) for value in inputs],
            }
            edges[node_id] = dependencies
            input_bindings[node_id] = bindings

            output_key = _varnode_key(output)
            if output_key is not None:
                last_def[output_key] = node_id

    return nodes, edges, input_bindings


def _slice_from_definition(
    root_definition: str | None,
    direct_root: dict[str, Any] | None,
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, list[str]],
    input_bindings: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered: list[str] = []
    visited: set[str] = set()
    roots: dict[tuple[str, str, int], dict[str, Any]] = {}

    def add_root(value: dict[str, Any]) -> None:
        key = _varnode_key(value)
        if key is None:
            raise ValueError("structured root varnode missing key")
        roots.setdefault(key, dict(value))

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        if node_id not in nodes:
            raise ValueError(f"missing p-code dependency node {node_id}")
        visited.add(node_id)
        for binding in input_bindings[node_id]:
            dependency = binding["definition"]
            if dependency is None:
                add_root(binding["varnode"])
            else:
                visit(dependency)
        ordered.append(node_id)

    if root_definition is None:
        if direct_root is None:
            raise ValueError("value slice has neither definition nor direct root")
        add_root(direct_root)
    else:
        visit(root_definition)

    slice_nodes = [
        {
            "id": node_id,
            "instruction": nodes[node_id]["instruction"],
            "opcode": nodes[node_id]["opcode"],
            "text": nodes[node_id]["text"],
        }
        for node_id in ordered
    ]
    return slice_nodes, [roots[key] for key in sorted(roots)]


def _classify_root(value: dict[str, Any]) -> dict[str, Any]:
    text = str(value.get("text") or "")
    space = str(value.get("space") or "").lower()
    upper = text.upper()
    if space == "const" and upper in {"RAM", "REGISTER", "UNIQUE"}:
        kind = "address-space-selector"
        blocker = False
    elif value.get("constant") is True or space == "const":
        kind = "constant"
        blocker = False
    elif value.get("register") is True and _FLOATING_REGISTER.fullmatch(upper):
        kind = "floating-register"
        blocker = True
    elif value.get("register") is True and _GENERAL_REGISTER.fullmatch(upper):
        kind = "general-register"
        blocker = True
    elif value.get("register") is True:
        kind = "other-register"
        blocker = True
    elif value.get("unique") is True or space == "unique":
        kind = "unresolved-unique"
        blocker = True
    else:
        kind = "external-or-memory-varnode"
        blocker = True
    return {**value, "root_kind": kind, "semantic_join_required": blocker}


def _direct_calls_before(
    instructions: list[dict[str, Any]], store_address: str
) -> list[dict[str, Any]]:
    limit = int(store_address, 0)
    result: list[dict[str, Any]] = []
    for instruction in instructions:
        address = _callsite._address(instruction.get("address"), field="instruction.address")
        if int(address, 0) >= limit:
            break
        if str(instruction.get("mnemonic") or "").upper() != "CALL":
            continue
        flows = instruction.get("flows")
        normalized: list[str] = []
        if isinstance(flows, list):
            for value in flows:
                if not isinstance(value, str):
                    continue
                try:
                    normalized.append(_callsite._address(value, field="call.flow"))
                except ValueError:
                    continue
        result.append(
            {
                "instruction": address,
                "text": instruction.get("text"),
                "direct_targets": normalized,
            }
        )
    return result


def analyze_bmw_body0_bind_pose_writer_value_provenance(
    target_role_path: Path,
    instruction_export: Path,
) -> dict[str, Any]:
    target_role = _load_json(target_role_path, TARGET_ROLE_FORMAT)
    target_parameter, witnesses = _validate_target_role(target_role)

    row = _read_single_instruction_row(instruction_export)
    function_address, instructions = _callsite._validate_instruction_row(row, instruction_export)
    if row.get("format") != INSTRUCTION_FORMAT:
        raise ValueError(f"{instruction_export}: expected {INSTRUCTION_FORMAT}")
    if function_address != POSE_WRITER:
        raise ValueError(f"{instruction_export}: expected exact {POSE_WRITER} row")

    instruction_by_address = {
        _callsite._address(item.get("address"), field="instruction.address"): item
        for item in instructions
    }
    nodes, edges, input_bindings = _structured_pcode_graph(instructions)

    writes: list[dict[str, Any]] = []
    structural_blockers: list[dict[str, Any]] = []
    root_kind_counts: dict[str, int] = {}
    all_roots: list[dict[str, Any]] = []

    for witness in witnesses:
        address = witness["instruction"]
        instruction = instruction_by_address.get(address)
        if instruction is None:
            raise ValueError(f"target-role witness instruction missing from export: {address}")
        pcode = instruction.get("pcode")
        if not isinstance(pcode, list):
            raise ValueError(f"{address}: pcode missing")
        stores: list[tuple[int, dict[str, Any]]] = []
        for op_index, operation in enumerate(pcode):
            if isinstance(operation, dict) and str(operation.get("opcode") or "").upper() == "STORE":
                stores.append((op_index, operation))
        if len(stores) != 1:
            structural_blockers.append(
                {
                    "id": "pose-store-pcode-cardinality-not-one",
                    "instruction": address,
                    "store_pcode_count": len(stores),
                }
            )
            continue

        op_index, operation = stores[0]
        inputs = operation.get("inputs")
        if not isinstance(inputs, list) or len(inputs) < 3:
            structural_blockers.append(
                {
                    "id": "pose-store-value-input-missing",
                    "instruction": address,
                }
            )
            continue
        source = _validate_varnode(inputs[2], context=f"{address}:{op_index}:STORE-value")
        node_id = f"{address}:{op_index}"
        binding_rows = input_bindings.get(node_id)
        if not isinstance(binding_rows, list) or len(binding_rows) < 3:
            raise ValueError(f"{node_id}: STORE input bindings missing")
        source_definition = binding_rows[2]["definition"]
        slice_nodes, roots_raw = _slice_from_definition(
            source_definition,
            None if source_definition is not None else source,
            nodes,
            edges,
            input_bindings,
        )
        roots = [_classify_root(root) for root in roots_raw]
        for root in roots:
            root_kind = root["root_kind"]
            root_kind_counts[root_kind] = root_kind_counts.get(root_kind, 0) + 1
            all_roots.append(root)

        opcodes = sorted({node["opcode"] for node in slice_nodes})
        contains_load = "LOAD" in opcodes
        contains_call = "CALL" in opcodes or "CALLIND" in opcodes
        floating_roots = [root for root in roots if root["root_kind"] == "floating-register"]
        preceding_calls = _direct_calls_before(instructions, address)
        writes.append(
            {
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "target_parameter_ordinal": target_parameter["ordinal"],
                "target_parameter_storage": target_parameter.get("storage"),
                "displacement": witness.get("displacement"),
                "displacement_hex": witness.get("displacement_hex"),
                "store_width": witness.get("store_width"),
                "required_bytes_touched": list(witness.get("required_bytes_touched") or []),
                "store_pcode_node": node_id,
                "store_value_varnode": dict(source),
                "store_value_definition": source_definition,
                "dependency_slice": slice_nodes,
                "dependency_opcodes": opcodes,
                "terminal_roots": roots,
                "contains_memory_load": contains_load,
                "contains_pcode_call": contains_call,
                "floating_register_roots": floating_roots,
                "preceding_direct_calls": preceding_calls,
                "value_semantics_proven": False,
            }
        )

    frontier_ready = len(writes) == len(witnesses) and not structural_blockers
    blockers = list(structural_blockers)

    if any(root["root_kind"] == "floating-register" for root in all_roots):
        blockers.append(
            {
                "id": "floating-register-call-return-provenance-unresolved",
                "evidence_state": "finite-worklist",
                "required_evidence": (
                    "join each floating-register terminal root to its exact producer; a preceding CALL is not itself proof that the callee produced ST0/XMM"
                ),
            }
        )
    if any(root["root_kind"] == "general-register" for root in all_roots):
        blockers.append(
            {
                "id": "general-register-source-root-semantics-unresolved",
                "evidence_state": "finite-worklist",
                "required_evidence": (
                    "join each terminal general-register value to physical ABI/caller provenance without assigning roles from register position"
                ),
            }
        )
    if any(write["contains_memory_load"] for write in writes):
        blockers.append(
            {
                "id": "pose-source-memory-load-address-semantics-unresolved",
                "evidence_state": "finite-worklist",
                "required_evidence": (
                    "prove the object/stack/global identity and byte layout of every LOAD feeding admitted pose STORE values"
                ),
            }
        )
    if any(root["root_kind"] in {"unresolved-unique", "other-register", "external-or-memory-varnode"} for root in all_roots):
        blockers.append(
            {
                "id": "pose-source-terminal-root-unresolved",
                "evidence_state": "blocked",
                "required_evidence": "resolve remaining structured p-code terminal roots before value promotion",
            }
        )

    blockers.extend(
        [
            {
                "id": "instruction-pcode-not-cfg-ssa",
                "evidence_state": "guard",
                "required_evidence": (
                    "use path-aware machine/register/stack provenance for any value crossing control-flow joins; linear instruction-pcode def/use is discovery only"
                ),
            },
            {
                "id": "BODY0-target-parameter-callsite-value-join-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "join the proven BODY-record target parameter at the selected initialization callsite to exact BMW chassis BODY0"
                ),
            },
            {
                "id": "bind-origin-basis-concrete-values-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "resolve every admitted pose STORE dependency to source-backed bind-time values before constructing M_BODY0_bind"
                ),
            },
        ]
    )

    return {
        "format": FORMAT,
        "inputs": {
            "pose_writer_target_role": str(target_role_path),
            "pose_writer_instruction_export": str(instruction_export),
        },
        "target": {
            "pose_writer": POSE_WRITER,
            "BODY_pose_target_parameter": target_parameter,
            "pose_write_witness_count": len(witnesses),
        },
        "analysis": {
            "analyzed_pose_store_count": len(writes),
            "all_target_role_pose_stores_analyzed": frontier_ready,
            "pose_store_values": writes,
            "terminal_root_kind_counts": dict(sorted(root_kind_counts.items())),
            "structural_blockers": structural_blockers,
        },
        "handoff": {
            "pose_writer_pose_store_value_dependency_frontier_ready": frontier_ready,
            "BODY0_bind_origin_basis_value_dependency_worklist_ready": frontier_ready,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "next_required_join": (
                "resolve terminal value roots with path-aware register/stack/x87 provenance, then join target parameter to BMW chassis BODY0"
                if frontier_ready
                else "repair structured pose STORE value extraction"
            ),
        },
        "blockers": blockers,
        "scope": {
            "structured_pcode_store_value_input_separated_from_address_input": True,
            "linear_instruction_pcode_dependency_frontier_only": True,
            "cfg_ssa_value_identity_proven": False,
            "preceding_CALL_used_as_floating_return_proof": False,
            "terminal_register_name_used_as_semantic_role": False,
            "host_floating_math_substitution_allowed": False,
            "pose_writer_candidate_promoted_to_bind_initializer": False,
            "BODY0_pointer_identity_proven": False,
            "BODY0_bind_matrix_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pose_writer_target_role", type=Path)
    parser.add_argument("pose_writer_instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_bmw_body0_bind_pose_writer_value_provenance(
        args.pose_writer_target_role,
        args.pose_writer_instruction_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

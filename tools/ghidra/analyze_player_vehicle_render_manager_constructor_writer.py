#!/usr/bin/env python3
"""Prove DAT_00bc185c non-null values are FUN_0045ef50 receiver instances.

The exhaustive DAT_00bc185c -> +0xca4 search is negative.  This pass therefore
moves to the independent writer/class-identity edge.  It consumes the exhaustive
negative runtime-alias artifact, the exact root-pose global-xref rank, and one
targeted instruction export containing only FUN_00d36210 and FUN_0045ef50.

The proof is deliberately narrow:

* every retail WRITE xref to DAT_00bc185c must be one of the two stores in
  FUN_00d36210;
* the non-null writer path passes the allocator result in ECX to FUN_0045ef50;
* every reachable FUN_0045ef50 RET returns its entry ECX receiver in EAX;
* FUN_0045ef50 still contains the independently frozen
  mPlayerVehicleRenderables receiver+0xca4 construction anchor;
* the alternate writer path stores zero.

A positive result proves the class identity of non-null DAT_00bc185c values.  It
does not prove a runtime +0xca4 access, player-renderable element ownership, VHF
root identity, frame equality, BODY0 bind-frame closure, or vehicle world pose.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_fun_00765470_body_owner_receiver as _register_engine

FORMAT = "SHIFT.PlayerVehicleRenderManagerGlobalConstructorIdentity/1"
ALIAS_FORMAT = "SHIFT.PlayerVehicleRenderablesRuntimeAlias/1"
RANK_FORMAT = "SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
CANDIDATE_GLOBAL = "0x00bc185c"
EXHAUSTIVE_XREF_FUNCTION_COUNT = 80

WRITER = "0x00d36210"
CONSTRUCTOR = "0x0045ef50"
ALLOCATOR = "0x008868c0"

WRITER_ZERO_ESI = "0x00d36224"
WRITER_ALLOC_SIZE = "0x00d362b9"
WRITER_ALLOC_CALL = "0x00d362be"
WRITER_NULL_CMP = "0x00d362d3"
WRITER_NULL_BRANCH = "0x00d362d5"
WRITER_RECEIVER_MOVE = "0x00d362d7"
WRITER_CTOR_CALL = "0x00d362d9"
WRITER_POST_CTOR_JUMP = "0x00d362de"
WRITER_GLOBAL_STORE = "0x00d362ec"
WRITER_NULL_STORE = "0x00d362f3"

CTOR_RECEIVER_SAVE = "0x0045ef59"
CTOR_LABEL_PUSH = "0x0045f191"
CTOR_CAPACITY_PUSH = "0x0045f196"
CTOR_ALLOC_CALL_1 = "0x0045f1a1"
CTOR_ALLOC_CALL_2 = "0x0045f1a8"
CTOR_ALLOC_CALL_3 = "0x0045f1af"
CTOR_FIELD_STORE = "0x0045f1bf"
CTOR_LABEL_ADDRESS = "0x00ab55a4"
CTOR_FIELD_OFFSET = 0xCA4

EXPECTED_WRITES = {
    (WRITER, WRITER_GLOBAL_STORE, "MOV [0x00bc185c],EAX"),
    (WRITER, WRITER_NULL_STORE, "MOV dword ptr [0x00bc185c],ESI"),
}

_MEMORY_CA4_RE = re.compile(
    r"^\s*(?:dword\s+ptr\s+)?\[\s*esi\s*\+\s*0x0*ca4\s*\]\s*$",
    re.IGNORECASE,
)
_PLAIN_HEX_OPERAND_RE = re.compile(r"^\s*0x([0-9a-f]+)\s*$", re.IGNORECASE)


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


def _addr(value: Any, *, field: str = "address") -> str:
    try:
        return _register_engine._normalize_address(value)
    except ValueError as exc:
        raise ValueError(f"{field}: {exc}") from exc


def _load_exhaustive_alias(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != ALIAS_FORMAT:
        raise ValueError(f"{path}: expected {ALIAS_FORMAT}")
    retail = report.get("retail")
    if not isinstance(retail, Mapping):
        raise ValueError("runtime-alias retail identity missing")
    if retail.get("program") != PROGRAM or str(retail.get("md5") or "").lower() != PE_MD5:
        raise ValueError("runtime-alias retail identity drift")
    candidate = report.get("candidate_global")
    if not isinstance(candidate, Mapping) or _addr(candidate.get("address")) != CANDIDATE_GLOBAL:
        raise ValueError("runtime-alias candidate-global drift")
    analysis = report.get("analysis")
    if not isinstance(analysis, Mapping):
        raise ValueError("runtime-alias analysis missing")
    if analysis.get("selected_function_count") != EXHAUSTIVE_XREF_FUNCTION_COUNT:
        raise ValueError("runtime-alias input is not the exhaustive 80-function xref sweep")
    if analysis.get("exact_candidate_global_value_alias_count") != 0:
        raise ValueError("runtime-alias branch is not exhaustively negative")
    if analysis.get("pcode_backed_ca4_access_count") != 0:
        raise ValueError("runtime-alias contains a +0xca4 candidate and must be resolved first")
    if report.get("ready") is not False:
        raise ValueError("runtime-alias exhaustive negative artifact unexpectedly ready")
    return report


def _load_rank(path: Path) -> dict[str, Any]:
    rank = _load_json(path)
    if rank.get("format") != RANK_FORMAT or rank.get("ready") is not True:
        raise ValueError(f"{path}: expected ready {RANK_FORMAT}")
    retail = rank.get("retail")
    if not isinstance(retail, Mapping):
        raise ValueError("rank retail identity missing")
    if retail.get("program") != PROGRAM or str(retail.get("md5") or "").lower() != PE_MD5:
        raise ValueError("rank retail identity drift")
    candidate = rank.get("candidate_global")
    if not isinstance(candidate, Mapping) or _addr(candidate.get("address")) != CANDIDATE_GLOBAL:
        raise ValueError("rank candidate-global drift")
    ranking = rank.get("ranking")
    if not isinstance(ranking, Mapping):
        raise ValueError("rank ranking section missing")
    if ranking.get("ranked_function_count") != EXHAUSTIVE_XREF_FUNCTION_COUNT:
        raise ValueError("rank does not cover the frozen 80-function global-xref set")
    selected = ranking.get("selected_instruction_export_functions")
    if not isinstance(selected, list) or len(selected) != EXHAUSTIVE_XREF_FUNCTION_COUNT:
        raise ValueError("rank is not the exhaustive 80-function acquisition artifact")

    writes: set[tuple[str, str, str]] = set()
    for row in ranking.get("functions") or []:
        if not isinstance(row, Mapping):
            continue
        function = _addr(row.get("function"), field="ranking.function")
        for site in row.get("reference_sites") or []:
            if not isinstance(site, Mapping) or str(site.get("type") or "").upper() != "WRITE":
                continue
            instruction = _addr(site.get("from"), field="reference_sites.from")
            writes.add((function, instruction, str(site.get("instruction") or "")))
    if writes != EXPECTED_WRITES:
        raise ValueError(f"candidate-global WRITE-xref set drift: {sorted(writes)!r}")
    return rank


def _load_instruction_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT or row.get("program") != PROGRAM:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT} for {PROGRAM}")
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        instructions = row.get("instructions")
        if not isinstance(function, Mapping) or not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{path}: malformed instruction row")
        address = _addr(function.get("address"), field="function.address")
        if address in rows:
            raise ValueError(f"{path}: duplicate function row {address}")
        if row.get("instruction_count") != len(instructions):
            raise ValueError(f"{address}: instruction count mismatch")
        rows[address] = row
    expected = {WRITER, CONSTRUCTOR}
    if set(rows) != expected:
        raise ValueError(
            "constructor/writer export target set drift; "
            f"missing={sorted(expected - set(rows))}, extra={sorted(set(rows) - expected)}"
        )
    return rows


def _by_address(row: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for instruction in row.get("instructions") or []:
        if not isinstance(instruction, dict):
            raise ValueError("instruction row contains a non-object instruction")
        address = _addr(instruction.get("address"), field="instruction.address")
        if address in result:
            raise ValueError(f"duplicate instruction {address}")
        result[address] = instruction
    return result


def _operands(instruction: Mapping[str, Any]) -> list[str]:
    values = instruction.get("operands")
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError(f"{instruction.get('address')}: operands must be a string list")
    return values


def _operand_equivalent(actual: str, expected: str) -> bool:
    """Treat only plain hex immediates as numeric; keep structural operands exact."""
    if actual.strip().upper() == expected.strip().upper():
        return True
    actual_match = _PLAIN_HEX_OPERAND_RE.fullmatch(actual)
    expected_match = _PLAIN_HEX_OPERAND_RE.fullmatch(expected)
    if actual_match is None or expected_match is None:
        return False
    return int(actual_match.group(1), 16) == int(expected_match.group(1), 16)


def _require_instruction(
    by_address: Mapping[str, dict[str, Any]],
    address: str,
    mnemonic: str,
    operands: list[str] | None = None,
) -> dict[str, Any]:
    instruction = by_address.get(address)
    if instruction is None:
        raise ValueError(f"missing required instruction {address}")
    if str(instruction.get("mnemonic") or "").upper() != mnemonic.upper():
        raise ValueError(f"{address}: expected {mnemonic}")
    actual = _operands(instruction)
    if operands is not None and (
        len(actual) != len(operands)
        or not all(_operand_equivalent(left, right) for left, right in zip(actual, operands))
    ):
        raise ValueError(f"{address}: operand drift: {actual!r}")
    return instruction


def _direct_target(instruction: Mapping[str, Any]) -> str | None:
    operands = _operands(instruction)
    if len(operands) != 1:
        return None
    token = operands[0].strip()
    try:
        operand_target = _addr(token)
    except ValueError:
        return None
    flows = instruction.get("flows")
    if isinstance(flows, list) and flows:
        normalized = []
        for value in flows:
            if not isinstance(value, str):
                return None
            try:
                normalized.append(_addr(value))
            except ValueError:
                return None
        if operand_target not in normalized:
            return None
    return operand_target


def _incoming_states(instructions: list[dict[str, Any]]) -> dict[str, Any]:
    by_address = {
        _addr(instruction.get("address"), field="instruction.address"): instruction
        for instruction in instructions
    }
    address_set = set(by_address)
    entry = _addr(instructions[0].get("address"), field="function entry")
    incoming: dict[str, Any] = {entry: _register_engine._initial_state()}
    queue: deque[str] = deque((entry,))
    iterations = 0
    max_iterations = max(64, len(instructions) * 64)
    while queue:
        address = queue.popleft()
        iterations += 1
        if iterations > max_iterations:
            raise ValueError(f"{entry}: register provenance did not converge")
        after = _register_engine._transfer(by_address[address], incoming[address])
        for successor in _register_engine._successors(by_address[address], address_set):
            merged, changed = _register_engine._merge(incoming.get(successor), after)
            if changed:
                incoming[successor] = merged
                queue.append(successor)
    return incoming


def _constructor_proof(row: Mapping[str, Any]) -> dict[str, Any]:
    instructions = row["instructions"]
    by_address = _by_address(row)
    _require_instruction(by_address, CTOR_RECEIVER_SAVE, "MOV", ["ESI", "ECX"])
    _require_instruction(by_address, CTOR_LABEL_PUSH, "PUSH", [CTOR_LABEL_ADDRESS])
    _require_instruction(by_address, CTOR_CAPACITY_PUSH, "PUSH", ["0x400"])

    expected_calls = {
        CTOR_ALLOC_CALL_1: "0x00695e30",
        CTOR_ALLOC_CALL_2: "0x00695f10",
        CTOR_ALLOC_CALL_3: "0x0068a700",
    }
    for address, target in expected_calls.items():
        call = _require_instruction(by_address, address, "CALL")
        if _direct_target(call) != target:
            raise ValueError(f"{address}: constructor allocation-call target drift")

    field_store = _require_instruction(by_address, CTOR_FIELD_STORE, "MOV")
    field_operands = _operands(field_store)
    field_anchor_ready = (
        len(field_operands) == 2
        and _MEMORY_CA4_RE.fullmatch(field_operands[0]) is not None
        and field_operands[1].strip().upper() == "EAX"
    )
    if not field_anchor_ready:
        raise ValueError(f"{CTOR_FIELD_STORE}: receiver+0xca4 store drift")

    states = _incoming_states(instructions)
    returns: list[dict[str, Any]] = []
    for instruction in instructions:
        if str(instruction.get("mnemonic") or "").upper() not in {"RET", "RETF"}:
            continue
        address = _addr(instruction.get("address"), field="return.address")
        state = states.get(address)
        if state is None:
            continue
        origins = _register_engine._sorted_origins(state["EAX"])
        returns.append(
            {
                "instruction": address,
                "eax_origins_before_return": origins,
                "returns_entry_ecx_receiver": origins == ["entry:ECX"],
            }
        )
    if not returns:
        raise ValueError("constructor has no reachable RET instruction")
    all_returns_receiver = all(item["returns_entry_ecx_receiver"] for item in returns)
    return {
        "function": CONSTRUCTOR,
        "entry_receiver": "ECX",
        "receiver_saved_to": "ESI",
        "receiver_save_instruction": CTOR_RECEIVER_SAVE,
        "field_anchor": {
            "allocation_label_address": CTOR_LABEL_ADDRESS,
            "allocation_label": "mPlayerVehicleRenderables",
            "label_push_instruction": CTOR_LABEL_PUSH,
            "capacity_push_instruction": CTOR_CAPACITY_PUSH,
            "field_store_instruction": CTOR_FIELD_STORE,
            "field_offset": "+0xca4",
            "source_backed_anchor_ready": field_anchor_ready,
        },
        "reachable_returns": returns,
        "all_reachable_returns_entry_receiver": all_returns_receiver,
    }


def _writer_proof(row: Mapping[str, Any], constructor_returns_receiver: bool) -> dict[str, Any]:
    instructions = row["instructions"]
    by_address = _by_address(row)
    _require_instruction(by_address, WRITER_ZERO_ESI, "XOR", ["ESI", "ESI"])
    _require_instruction(by_address, WRITER_ALLOC_SIZE, "PUSH", ["0x46e0"])
    alloc_call = _require_instruction(by_address, WRITER_ALLOC_CALL, "CALL")
    if _direct_target(alloc_call) != ALLOCATOR:
        raise ValueError(f"{WRITER_ALLOC_CALL}: allocator target drift")
    _require_instruction(by_address, WRITER_NULL_CMP, "CMP", ["EAX", "ESI"])
    null_branch = _require_instruction(by_address, WRITER_NULL_BRANCH, "JZ", [WRITER_NULL_STORE])
    if _direct_target(null_branch) != WRITER_NULL_STORE:
        raise ValueError(f"{WRITER_NULL_BRANCH}: null-branch target drift")
    _require_instruction(by_address, WRITER_RECEIVER_MOVE, "MOV", ["ECX", "EAX"])
    ctor_call = _require_instruction(by_address, WRITER_CTOR_CALL, "CALL")
    if _direct_target(ctor_call) != CONSTRUCTOR:
        raise ValueError(f"{WRITER_CTOR_CALL}: constructor target drift")
    post_ctor = _require_instruction(by_address, WRITER_POST_CTOR_JUMP, "JMP", [WRITER_GLOBAL_STORE])
    if _direct_target(post_ctor) != WRITER_GLOBAL_STORE:
        raise ValueError(f"{WRITER_POST_CTOR_JUMP}: post-constructor target drift")
    _require_instruction(by_address, WRITER_GLOBAL_STORE, "MOV", ["[0x00bc185c]", "EAX"])
    _require_instruction(
        by_address,
        WRITER_NULL_STORE,
        "MOV",
        ["dword ptr [0x00bc185c]", "ESI"],
    )

    states = _incoming_states(instructions)
    ctor_state = states.get(WRITER_CTOR_CALL)
    null_store_state = states.get(WRITER_NULL_STORE)
    if ctor_state is None or null_store_state is None:
        raise ValueError("writer constructor or null-store path is unreachable")
    ecx_origins = _register_engine._sorted_origins(ctor_state["ECX"])
    eax_origins = _register_engine._sorted_origins(ctor_state["EAX"])
    receiver_is_allocator_result = len(ecx_origins) == 1 and ecx_origins == eax_origins
    null_origins = _register_engine._sorted_origins(null_store_state["ESI"])
    null_store_is_zero = null_origins == ["immediate:0"]

    continuity_ready = (
        receiver_is_allocator_result
        and constructor_returns_receiver
        and null_store_is_zero
    )
    return {
        "function": WRITER,
        "allocation_size": "0x46e0",
        "allocator_target": ALLOCATOR,
        "constructor_target": CONSTRUCTOR,
        "constructor_call_instruction": WRITER_CTOR_CALL,
        "constructor_receiver_register": "ECX",
        "receiver_origins_at_constructor_call": ecx_origins,
        "allocator_result_origins_at_constructor_call": eax_origins,
        "receiver_is_same_physical_allocator_result": receiver_is_allocator_result,
        "non_null_global_store_instruction": WRITER_GLOBAL_STORE,
        "null_global_store_instruction": WRITER_NULL_STORE,
        "null_store_esi_origins": null_origins,
        "null_store_is_zero": null_store_is_zero,
        "constructor_result_to_global_continuity_ready": continuity_ready,
    }


def analyze(alias_path: Path, rank_path: Path, instruction_export: Path) -> dict[str, Any]:
    alias = _load_exhaustive_alias(alias_path)
    rank = _load_rank(rank_path)
    rows = _load_instruction_rows(instruction_export)

    constructor = _constructor_proof(rows[CONSTRUCTOR])
    writer = _writer_proof(
        rows[WRITER],
        bool(constructor["all_reachable_returns_entry_receiver"]),
    )
    ready = bool(
        constructor["field_anchor"]["source_backed_anchor_ready"]
        and constructor["all_reachable_returns_entry_receiver"]
        and writer["constructor_result_to_global_continuity_ready"]
    )

    blockers: list[dict[str, Any]] = []
    if not constructor["all_reachable_returns_entry_receiver"]:
        blockers.append(
            {
                "id": "render-manager-constructor-return-receiver-identity-unproven",
                "evidence_state": "blocked",
                "required_evidence": "every reachable FUN_0045ef50 return must carry entry ECX in EAX",
            }
        )
    if not writer["constructor_result_to_global_continuity_ready"]:
        blockers.append(
            {
                "id": "render-manager-constructor-result-to-global-continuity-unproven",
                "evidence_state": "blocked",
                "required_evidence": "writer must store the same constructed receiver or zero into DAT_00bc185c",
            }
        )
    blockers.extend(
        [
            {
                "id": "proven-render-manager-to-player-renderables-runtime-owner-transfer-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "from the now-proven DAT_00bc185c manager receiver, trace a called manager method or "
                    "equivalent physical flow to receiver+0xca4 and then to the SMS/RenderHierarchy owner"
                ),
            },
            {
                "id": "outer-vehicle-root-to-VHF-vehicle-root-frame-relation-unproven",
                "evidence_state": "unknown",
                "required_evidence": "join the proven render owner to canonical BMW VHF root/frame identity",
            },
        ]
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "candidate-global-render-manager-constructor-identity-ready"
            if ready
            else "candidate-global-render-manager-constructor-identity-blocked"
        ),
        "ready": ready,
        "retail": {"program": PROGRAM, "md5": PE_MD5},
        "candidate_global": {
            "address": CANDIDATE_GLOBAL,
            "all_write_xrefs_accounted_for": True,
            "write_xref_count": len(EXPECTED_WRITES),
            "non_null_values_are_FUN_0045ef50_receivers": ready,
        },
        "inputs": {
            "runtime_alias": {
                "format": alias["format"],
                "selected_function_count": alias["analysis"]["selected_function_count"],
                "exhaustive_direct_ca4_alias_branch_negative": True,
            },
            "root_pose_rank": {
                "format": rank["format"],
                "ranked_function_count": rank["ranking"]["ranked_function_count"],
                "selected_function_count": len(rank["ranking"]["selected_instruction_export_functions"]),
                "candidate_global_write_xrefs_exhaustive": True,
            },
            "instruction_export": {
                "format": INSTRUCTION_FORMAT,
                "functions": [WRITER, CONSTRUCTOR],
            },
        },
        "analysis": {
            "writer": writer,
            "constructor": constructor,
        },
        "handoff": {
            "candidate_global_render_manager_class_identity_ready": ready,
            "candidate_global_non_null_FUN_0045ef50_receiver_ready": ready,
            "constructor_player_vehicle_renderables_layout_anchor_ready": bool(
                constructor["field_anchor"]["source_backed_anchor_ready"]
            ),
            "candidate_global_to_ca4_runtime_field_base_alias_ready": False,
            "player_vehicle_renderables_field_runtime_access_ready": False,
            "player_vehicle_renderables_owner_join_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "scope": {
            "original_game_executed": False,
            "runtime_capture_required": False,
            "direct_global_to_ca4_branch_reopened": False,
            "constructor_callgraph_proximity_promoted_to_identity": False,
            "constructor_return_receiver_proven_by_all_path_register_provenance": True,
            "null_global_value_promoted_to_class_instance": False,
            "player_renderables_collection_promoted_to_VHF_root": False,
            "frame_identity_claimed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exhaustive_runtime_alias", type=Path)
    parser.add_argument("exhaustive_root_pose_rank", type=Path)
    parser.add_argument("constructor_writer_instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = analyze(
            args.exhaustive_runtime_alias,
            args.exhaustive_root_pose_rank,
            args.constructor_writer_instruction_export,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 2
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

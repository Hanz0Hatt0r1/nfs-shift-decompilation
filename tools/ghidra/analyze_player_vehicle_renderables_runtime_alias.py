#!/usr/bin/env python3
"""Prove physical candidate-global -> +0xca4 runtime receiver continuity.

This pass consumes either the current root-pose-aware render-manager rank or the
older compatible global-xref rank plus the bounded
SHIFT.GhidraFunctionInstructions/2 export selected by that ranker. It uses the
existing all-path IA-32 register provenance engine and structured Ghidra p-code
to answer one narrow question: does a selected function load the candidate
global's pointer value and then use that exact physical value as the base of a
+0xca4 memory access?

Matching that physical access against the independently proven constructor
layout establishes only a global-value -> layout-field alias. It does not prove
the global's class identity, element identity, VHF hierarchy identity, or frame
equality.
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
import analyze_register_relative_accesses as _accesses

FORMAT = "SHIFT.PlayerVehicleRenderablesRuntimeAlias/1"
RANK_FORMAT = "SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1"
ROOT_POSE_RANK_FORMAT = "SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1"
RANK_FORMATS = frozenset((RANK_FORMAT, ROOT_POSE_RANK_FORMAT))
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
FIELD_OFFSET = 0xCA4
_TRACKED = tuple(_register_engine._TRACKED)
_ADDRESS_TOKEN_RE = re.compile(r"(?:0x|dat_)([0-9a-f]+)", re.IGNORECASE)
_BARE_MEMORY_ADDRESS_RE = re.compile(r"\[0*([0-9a-f]{6,8})\]", re.IGNORECASE)


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


def _load_rank(path: Path) -> tuple[dict[str, Any], str, list[str]]:
    rank = _load_json(path)
    rank_format = rank.get("format")
    if rank_format not in RANK_FORMATS or rank.get("ready") is not True:
        expected = " or ".join(sorted(RANK_FORMATS))
        raise ValueError(f"{path}: expected ready {expected}")
    retail = rank.get("retail")
    if not isinstance(retail, Mapping):
        raise ValueError("rank retail identity missing")
    if retail.get("program") != PROGRAM or str(retail.get("md5") or "").lower() != PE_MD5:
        raise ValueError("rank retail identity drift")

    if rank_format == ROOT_POSE_RANK_FORMAT:
        handoff = rank.get("handoff")
        if not isinstance(handoff, Mapping):
            raise ValueError("root-pose rank handoff missing")
        if handoff.get("root_pose_positive_anchor_ranking_ready") is not True:
            raise ValueError("root-pose rank positive-anchor gate is not ready")
        if handoff.get("collision_wheel_LOD_anchor_removed_from_positive_render_score") is not True:
            raise ValueError("root-pose rank collision-negative-control gate is not ready")

    candidate = rank.get("candidate_global")
    if not isinstance(candidate, Mapping):
        raise ValueError("rank candidate_global missing")
    global_address = _addr(candidate.get("address"), field="candidate_global.address")
    if candidate.get("runtime_manager_instance_identity_proven") is not False:
        raise ValueError("rank unexpectedly preclaims manager instance identity")

    ranking = rank.get("ranking")
    if not isinstance(ranking, Mapping):
        raise ValueError("rank ranking section missing")
    selected_raw = ranking.get("selected_instruction_export_functions")
    if not isinstance(selected_raw, list) or not selected_raw:
        raise ValueError("rank selected instruction-export worklist is empty")
    selected = [_addr(value, field="selected function") for value in selected_raw]
    if len(set(selected)) != len(selected):
        raise ValueError("rank selected worklist contains duplicates")
    return rank, global_address, selected


def _load_instruction_rows(path: Path, selected: list[str]) -> dict[str, dict[str, Any]]:
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
    if set(rows) != set(selected):
        missing = sorted(set(selected) - set(rows), key=lambda value: int(value, 16))
        extra = sorted(set(rows) - set(selected), key=lambda value: int(value, 16))
        raise ValueError(
            f"instruction target set disagrees with rank worklist; missing={missing}, extra={extra}"
        )
    return rows


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


def _normalize_origin_text(value: str) -> str:
    return re.sub(r"\s+", "", value.lower())


def _origin_mentions_global(origin: str, global_address: str) -> bool:
    """Compare Ghidra absolute/DAT renderings numerically, ignoring zero padding."""
    if not origin.startswith("memory:"):
        return False
    normalized = _normalize_origin_text(origin)
    expected = int(global_address, 16)
    for match in _ADDRESS_TOKEN_RE.finditer(normalized):
        try:
            if int(match.group(1), 16) == expected:
                return True
        except ValueError:
            continue
    for match in _BARE_MEMORY_ADDRESS_RE.finditer(normalized):
        try:
            if int(match.group(1), 16) == expected:
                return True
        except ValueError:
            continue
    return False


def _instruction_by_address(row: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _addr(instruction.get("address"), field="instruction.address"): instruction
        for instruction in row.get("instructions") or []
    }


def _field_access_candidates(instruction_export: Path) -> list[dict[str, Any]]:
    report = _accesses.analyze_register_relative_accesses(instruction_export)
    return [
        access
        for access in report.get("accesses") or []
        if int(access.get("displacement", -1)) == FIELD_OFFSET
    ]


def analyze(rank_path: Path, instruction_export: Path) -> dict[str, Any]:
    rank, global_address, selected = _load_rank(rank_path)
    rank_format = str(rank["format"])
    rows = _load_instruction_rows(instruction_export, selected)
    field_accesses = _field_access_candidates(instruction_export)

    states = {
        function: _incoming_states(row["instructions"])
        for function, row in rows.items()
    }
    by_instruction = {
        function: _instruction_by_address(row)
        for function, row in rows.items()
    }

    analyses: list[dict[str, Any]] = []
    proven_aliases: list[dict[str, Any]] = []
    for access in field_accesses:
        function = _addr(access.get("function"), field="access.function")
        instruction = _addr(access.get("instruction"), field="access.instruction")
        base = str(access.get("base_register") or "").upper()
        if base not in _TRACKED:
            continue
        state = states[function].get(instruction)
        if state is None:
            raise ValueError(f"{function}:{instruction}: +0xca4 access is unreachable")
        origins = _register_engine._sorted_origins(state[base])
        matching = [origin for origin in origins if _origin_mentions_global(origin, global_address)]
        exact_alias = len(origins) == 1 and len(matching) == 1
        instruction_row = by_instruction[function][instruction]
        item = {
            "function": function,
            "function_name": access.get("function_name"),
            "instruction": instruction,
            "instruction_text": instruction_row.get("text"),
            "access": access.get("access"),
            "base_register": base,
            "field_offset": FIELD_OFFSET,
            "field_offset_hex": "+0xca4",
            "base_origins_before_access": origins,
            "candidate_global_memory_origins": matching,
            "exact_single_candidate_global_value_as_field_base": exact_alias,
            "pcode_memory_ops": access.get("pcode_memory_ops"),
            "semantic_manager_class_identity_proven": False,
            "semantic_player_vehicle_renderables_identity_proven": False,
        }
        analyses.append(item)
        if exact_alias:
            proven_aliases.append(item)

    rank_functions = {
        str(row.get("function")): row
        for row in (rank.get("ranking") or {}).get("functions") or []
        if isinstance(row, Mapping)
    }
    proven_with_vehicle_proximity = [
        item
        for item in proven_aliases
        if isinstance(rank_functions.get(item["function"]), Mapping)
        and rank_functions[item["function"]].get("minimum_vehicle_anchor_distance") is not None
    ]

    ready = bool(proven_aliases)
    blockers: list[dict[str, Any]] = []
    if not proven_aliases:
        blockers.append(
            {
                "id": "candidate-global-to-ca4-field-base-alias-not-found",
                "evidence_state": "blocked",
                "required_evidence": (
                    "selected instruction export must contain a p-code-backed +0xca4 access whose "
                    "base register has exactly one all-path origin loaded from the candidate global"
                ),
            }
        )
    blockers.extend(
        [
            {
                "id": "candidate-global-render-manager-class-identity-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "join the globally sourced receiver to the constructor/vtable class identity "
                    "independently of field-offset coincidence"
                ),
            },
            {
                "id": "ca4-field-value-to-car-body-visual-owner-transfer-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "trace the value loaded from globally sourced receiver+0xca4 into the proven "
                    "HDVehicle/car-body/visual owner lane"
                ),
            },
            {
                "id": "outer-vehicle-root-to-VHF-vehicle-root-frame-relation-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "join the proven player-renderable owner to canonical BMW VHF hierarchy/root "
                    "identity or fixed affine relation"
                ),
            },
        ]
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "candidate-global-ca4-runtime-alias-ready"
            if ready
            else "candidate-global-ca4-runtime-alias-blocked"
        ),
        "ready": ready,
        "retail": {"program": PROGRAM, "md5": PE_MD5},
        "input_rank": {
            "format": rank_format,
            "root_pose_aware_rank": rank_format == ROOT_POSE_RANK_FORMAT,
        },
        "candidate_global": {
            "address": global_address,
            "runtime_manager_class_identity_proven": False,
        },
        "constructor_layout_anchor": {
            "function": "0x0045ef50",
            "field_offset": "+0xca4",
            "allocation_label": "mPlayerVehicleRenderables",
            "constructor_field_relation_source_backed": True,
            "same_offset_proves_same_class": False,
        },
        "analysis": {
            "selected_function_count": len(selected),
            "pcode_backed_ca4_access_count": len(analyses),
            "exact_candidate_global_value_alias_count": len(proven_aliases),
            "exact_alias_with_bounded_vehicle_callgraph_proximity_count": len(
                proven_with_vehicle_proximity
            ),
            "field_accesses": analyses,
        },
        "handoff": {
            "candidate_global_to_ca4_runtime_field_base_alias_ready": ready,
            "player_vehicle_renderables_field_runtime_access_ready": ready,
            "candidate_global_render_manager_class_identity_ready": False,
            "player_vehicle_renderables_owner_join_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "scope": {
            "original_game_executed": False,
            "runtime_capture_required": False,
            "structured_pcode_required_for_ca4_access": True,
            "all_path_register_provenance_required": True,
            "candidate_global_promoted_to_render_manager_class": False,
            "field_offset_coincidence_promoted_to_class_identity": False,
            "callgraph_proximity_promoted_to_pointer_identity": False,
            "ca4_field_promoted_to_VHF_root": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rank_artifact", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = analyze(args.rank_artifact, args.instruction_export)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

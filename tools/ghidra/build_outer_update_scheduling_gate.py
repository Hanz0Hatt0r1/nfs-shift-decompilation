#!/usr/bin/env python3
"""Narrow the static scheduling frontier immediately above FUN_00770e80.

The existing SHIFT.OuterUpdateCallsiteStatic/1 contract proves the direct
FUN_00713050 -> FUN_00794a30 -> FUN_00770e80 execution chain and records that
FUN_00794a30 gates its outer-update call on ``param_5 != 0``.  This stage reopens
only the pinned recovered source body of FUN_00713050 and asks a narrower
question: which of its three source-visible FUN_00794a30 calls can satisfy that
explicit gate argument?

The result is deliberately not a cadence proof.  Source call order is not
silently equated with Ghidra machine-call instruction order, and one statically
gate-eligible source call does not prove how many times that statement executes
per frame/fixed step or who owns the enclosing schedule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.OuterUpdateSchedulingGate/1"
CALLSITE_FORMAT = "SHIFT.OuterUpdateCallsiteStatic/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"

OUTER_UPDATE = "0x00770e80"
FIRST_CALLER = "0x00794a30"
UPSTREAM_BATCH = "0x00713050"
UPSTREAM_OWNER = "0x00715380"
FIRST_CALLER_NAME = "FUN_00794a30"
UPSTREAM_BATCH_NAME = "FUN_00713050"
EXPECTED_PARAM5_GATE = "param_5 != 0"


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _norm_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError:
        return None


def _extract_function_body(source: str, name: str) -> str:
    pattern = re.compile(
        rf"(?m)^(?:{re.escape(name)}|[^\s\n][^\n]*\b{re.escape(name)})\s*\("
    )
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError(
            f"{name}: expected exactly one function definition; found {len(matches)}"
        )
    brace = source.find("{", matches[0].end())
    if brace < 0:
        raise ValueError(f"{name}: opening brace not found")
    depth = 0
    end = None
    quote: str | None = None
    escaped = False
    for index in range(brace, len(source)):
        char = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
    if end is None:
        raise ValueError(f"{name}: closing brace not found")
    return source[brace + 1 : end]


def _extract_calls(body: str, name: str) -> list[str]:
    token = f"{name}("
    result: list[str] = []
    cursor = 0
    while True:
        start = body.find(token, cursor)
        if start < 0:
            return result
        open_paren = start + len(name)
        depth = 0
        quote: str | None = None
        escaped = False
        end = None
        for index in range(open_paren, len(body)):
            char = body[index]
            if quote is not None:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in {"'", '"'}:
                quote = char
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise ValueError(f"{name}: unterminated call expression")
        result.append(body[start:end])
        cursor = end


def _split_call_arguments(call: str, name: str) -> list[str]:
    prefix = f"{name}("
    if not call.startswith(prefix) or not call.endswith(")"):
        raise ValueError(f"malformed {name} call expression")
    inner = call[len(prefix) : -1]
    args: list[str] = []
    start = 0
    paren = bracket = brace = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(inner):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket -= 1
        elif char == "{":
            brace += 1
        elif char == "}":
            brace -= 1
        elif char == "," and paren == bracket == brace == 0:
            args.append(inner[start:index].strip())
            start = index + 1
        if paren < 0 or bracket < 0 or brace < 0:
            raise ValueError(f"{name}: malformed nested call arguments")
    if quote is not None or paren or bracket or brace:
        raise ValueError(f"{name}: malformed nested call arguments")
    args.append(inner[start:].strip())
    return args


def _constant_gate_value(text: str) -> int | None:
    token = re.sub(r"\s+", "", text)
    zero_tokens = {"0", "'\\0'", "'\\x00'", "'\\x0'"}
    one_tokens = {"1", "'\\1'", "'\\x01'", "'\\x1'"}
    if token in zero_tokens:
        return 0
    if token in one_tokens:
        return 1
    return None


def _validated_machine_calls(batch: dict[str, Any]) -> list[dict[str, Any]]:
    rows = batch.get("direct_calls_to_first_caller")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("upstream batch must retain exactly three direct caller edges")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("upstream batch contains invalid direct call edge")
        if _norm_address(row.get("from_function")) != UPSTREAM_BATCH:
            raise ValueError("upstream batch direct edge source drift")
        if _norm_address(row.get("to")) != FIRST_CALLER:
            raise ValueError("upstream batch direct edge target drift")
        if row.get("indirect") is not False:
            raise ValueError("upstream batch edge is no longer direct")
        instruction = _norm_address(row.get("instruction"))
        if instruction is None:
            raise ValueError("upstream batch direct edge has invalid instruction address")
        if instruction in seen:
            raise ValueError("upstream batch direct edges contain duplicate call instruction")
        seen.add(instruction)
        copied = dict(row)
        copied["instruction"] = instruction
        result.append(copied)
    return sorted(result, key=lambda row: int(row["instruction"], 16))


def _validate_callsite_contract(report: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scope = report.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("outer-update callsite scope missing")
    for key in (
        "source_snapshot_hash_verified",
        "ghidra_binary_identity_verified",
        "source_and_direct_callgraph_cross_checked",
    ):
        if scope.get(key) is not True:
            raise ValueError(f"outer-update callsite prerequisite not proven: {key}")
    if scope.get("rendered_frame_schedule_proven") is not False:
        raise ValueError("outer-update callsite contract unexpectedly preclaims frame cadence")

    outer = report.get("outer_update")
    if not isinstance(outer, dict) or _norm_address(outer.get("function")) != OUTER_UPDATE:
        raise ValueError("outer-update anchor drift")

    direct = report.get("direct_callsites")
    if not isinstance(direct, list):
        raise ValueError("outer-update direct callsites missing")
    matches = [
        row
        for row in direct
        if isinstance(row, dict) and _norm_address(row.get("caller")) == FIRST_CALLER
    ]
    if len(matches) != 1:
        raise ValueError("expected exactly one FUN_00794a30 callsite contract row")
    first_caller = matches[0]
    gate = first_caller.get("gate")
    if not isinstance(gate, list) or EXPECTED_PARAM5_GATE not in gate:
        raise ValueError("FUN_00794a30 param_5 gate is not proven by the input contract")
    ghidra_call = first_caller.get("ghidra_call")
    if not isinstance(ghidra_call, dict):
        raise ValueError("FUN_00794a30 outer-update Ghidra edge missing")
    if _norm_address(ghidra_call.get("from_function")) != FIRST_CALLER:
        raise ValueError("FUN_00794a30 outer-update edge source drift")
    if _norm_address(ghidra_call.get("to")) != OUTER_UPDATE:
        raise ValueError("FUN_00794a30 outer-update edge target drift")
    if ghidra_call.get("indirect") is not False:
        raise ValueError("FUN_00794a30 outer-update edge is no longer direct")

    batch = report.get("upstream_batch_path")
    if not isinstance(batch, dict) or _norm_address(batch.get("function")) != UPSTREAM_BATCH:
        raise ValueError("upstream batch anchor drift")
    if batch.get("first_caller_source_call_count") != 3:
        raise ValueError("upstream batch source call count drift")
    machine_calls = _validated_machine_calls(batch)

    owner = report.get("upstream_owner_path")
    if not isinstance(owner, dict) or _norm_address(owner.get("function")) != UPSTREAM_OWNER:
        raise ValueError("upstream owner anchor drift")
    owner_edge = owner.get("direct_call")
    if not isinstance(owner_edge, dict):
        raise ValueError("upstream owner direct edge missing")
    if _norm_address(owner_edge.get("from_function")) != UPSTREAM_OWNER:
        raise ValueError("upstream owner edge source drift")
    if _norm_address(owner_edge.get("to")) != UPSTREAM_BATCH:
        raise ValueError("upstream owner edge target drift")
    if owner_edge.get("indirect") is not False:
        raise ValueError("upstream owner edge is no longer direct")
    return first_caller, machine_calls


def build_outer_update_scheduling_gate(
    source_path: Path,
    callsite_contract_path: Path,
    *,
    expected_source_sha256: str = SOURCE_SHA256,
) -> dict[str, Any]:
    report = _load(callsite_contract_path, CALLSITE_FORMAT)
    first_caller, machine_calls = _validate_callsite_contract(report)

    source_bytes = source_path.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if source_sha256 != expected_source_sha256:
        raise ValueError(
            "unexpected SHIFT.exe.c SHA-256: "
            f"expected {expected_source_sha256}, got {source_sha256}"
        )
    source_meta = report.get("source")
    if not isinstance(source_meta, dict) or source_meta.get("sha256") != source_sha256:
        raise ValueError("source bytes do not match outer-update callsite contract")
    source = source_bytes.decode("utf-8", errors="strict")

    batch_body = _extract_function_body(source, UPSTREAM_BATCH_NAME)
    calls = _extract_calls(batch_body, FIRST_CALLER_NAME)
    if len(calls) != 3:
        raise ValueError(
            f"{UPSTREAM_BATCH_NAME}: expected exactly three source calls to {FIRST_CALLER_NAME}; "
            f"found {len(calls)}"
        )

    source_calls: list[dict[str, Any]] = []
    nonconstant_ordinals: list[int] = []
    nonzero_ordinals: list[int] = []
    for ordinal, call in enumerate(calls):
        args = _split_call_arguments(call, FIRST_CALLER_NAME)
        if len(args) != 6:
            raise ValueError(
                f"{UPSTREAM_BATCH_NAME}: {FIRST_CALLER_NAME} call {ordinal} has {len(args)} args"
            )
        gate_text = args[5]
        gate_value = _constant_gate_value(gate_text)
        if gate_value is None:
            nonconstant_ordinals.append(ordinal)
            gate_state = "unknown"
        elif gate_value == 0:
            gate_state = "blocked-by-param5-zero"
        else:
            nonzero_ordinals.append(ordinal)
            gate_state = "param5-gate-eligible"
        source_calls.append(
            {
                "source_ordinal": ordinal,
                "argument_count": len(args),
                "param5_argument_text": gate_text.strip(),
                "param5_constant_value": gate_value,
                "param5_gate_state": gate_state,
                "outer_update_guaranteed": False,
                "remaining_runtime_gate": "caller +0x234 == 0" if gate_value else None,
            }
        )

    unique_nonzero = len(nonzero_ordinals) == 1 and not nonconstant_ordinals
    blockers: list[str] = []
    if nonconstant_ordinals:
        blockers.append("one_or_more_FUN_00713050_param5_arguments_not_constant")
    if len(nonzero_ordinals) != 1:
        blockers.append("unique_nonzero_FUN_00713050_param5_call_not_proven")

    # These boundaries remain open even when the source gate cardinality is exact.
    blockers.extend(
        [
            "source_call_to_machine_callsite_identity_not_proven",
            "gate_eligible_statement_dynamic_execution_count_not_proven",
            "FUN_00713050_invocation_cadence_owner_not_proven",
            "FUN_0079b2d0_dispatch_owner_not_proven",
            "rendered_frame_relation_not_proven",
        ]
    )

    return {
        "format": FORMAT,
        "inputs": {
            "source": str(source_path),
            "outer_update_callsite_contract": str(callsite_contract_path),
        },
        "source_sha256": source_sha256,
        "outer_update": OUTER_UPDATE,
        "first_caller": FIRST_CALLER,
        "upstream_batch": UPSTREAM_BATCH,
        "upstream_owner": UPSTREAM_OWNER,
        "first_caller_param5_gate": EXPECTED_PARAM5_GATE,
        "source_calls_to_first_caller": source_calls,
        "source_call_count": len(source_calls),
        "constant_param5_sequence": [row["param5_constant_value"] for row in source_calls],
        "nonzero_param5_source_ordinals": nonzero_ordinals,
        "nonconstant_param5_source_ordinals": nonconstant_ordinals,
        "unique_nonzero_param5_source_call_proven": unique_nonzero,
        "unique_nonzero_param5_source_ordinal": nonzero_ordinals[0] if unique_nonzero else None,
        "machine_callsite_candidates": machine_calls,
        "source_to_machine_callsite_mapping_state": "unknown",
        "outer_update_dynamic_call_count_state": "unknown",
        "cadence_owner_state": "unknown",
        "next_instruction_targets": [UPSTREAM_BATCH],
        "blockers": sorted(set(blockers)),
        "vehicle_update_context": {
            "outer_receiver": (report.get("outer_update") or {}).get("receiver_at_callsites"),
            "caller_gate": list(first_caller.get("gate") or []),
            "outer_mode_argument": first_caller.get("outer_mode_argument"),
        },
        "scope": {
            "source_snapshot_hash_verified": True,
            "source_and_direct_callgraph_cross_checked_upstream": True,
            "three_source_calls_to_FUN_00794a30_proven": True,
            "param5_source_constants_recovered": not nonconstant_ordinals,
            "unique_param5_gate_eligible_source_call_proven": unique_nonzero,
            "source_order_equals_machine_instruction_order_assumed": False,
            "source_to_machine_callsite_mapping_proven": False,
            "remaining_caller_state_gate_proven_true": False,
            "dynamic_statement_execution_count_proven": False,
            "FUN_00713050_invocation_cadence_proven": False,
            "fixed_step_cadence_owner_proven": False,
            "rendered_frame_cadence_proven": False,
            "alternate_caller_dispatch_owner_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "note": (
                "The recovered source proves which FUN_00713050 source call(s) can satisfy "
                "FUN_00794a30's explicit param_5 != 0 gate. It does not map source ordinal to "
                "one exact machine CALL instruction and does not prove dynamic execution count, "
                "fixed-step ownership, or rendered-frame cadence."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="known recovered SHIFT.exe.c snapshot")
    parser.add_argument("outer_update_callsite_contract", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_outer_update_scheduling_gate(
        args.source,
        args.outer_update_callsite_contract,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"source calls: {report['source_call_count']}")
    print(
        "unique nonzero param_5 source call: "
        f"{report['unique_nonzero_param5_source_call_proven']}"
    )
    print(f"cadence owner: {report['cadence_owner_state']}")
    print(f"blockers: {len(report['blockers'])}")
    if args.json_out:
        print(f"json: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

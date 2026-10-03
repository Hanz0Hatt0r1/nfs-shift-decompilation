#!/usr/bin/env python3
"""Trace machine return origins for the exact returned-pointer target frontier.

This stage consumes the unresolved
SHIFT.VehicleReturnedAllocationPointerBoundary/1 plus the exact targeted
SHIFT.GhidraFunctionInstructions/2 export selected by that boundary.

It answers one narrow question only: for every reachable exit of every exact
frontier target, what immediate machine origin supplies EAX or the terminal tail
transfer?  The result can shrink the next static worklist without assigning an
allocation-pointer semantic role by convention.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, NamedTuple

FORMAT = "SHIFT.VehicleReturnedAllocationPointerReturnProvenance/1"
BOUNDARY_FORMAT = "SHIFT.VehicleReturnedAllocationPointerBoundary/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
EXPECTED_BLOCKER = "returned_allocation_pointer_semantic_role_not_proven"

FULL_GPRS = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
EAX_PARTIAL = {"AX", "AL", "AH"}
SIZE_PREFIX = re.compile(r"^(?:BYTE|WORD|DWORD|QWORD)\s+PTR\s+", re.IGNORECASE)


class Origin(NamedTuple):
    kind: str
    target: str | None = None
    instruction: str | None = None
    detail: str | None = None


ENTRY_EAX = Origin("function-entry-eax")


def _norm(value: Any) -> str | None:
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


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield value


def _load_boundary(path: Path) -> tuple[dict[str, Any], list[str]]:
    value = _load_json(path)
    if value.get("format") != BOUNDARY_FORMAT:
        raise ValueError(f"{path}: expected {BOUNDARY_FORMAT}")
    if value.get("returned_allocation_pointer_role_proven") is not False:
        raise ValueError("returned allocation-pointer boundary must remain unresolved")
    if value.get("returned_allocation_pointer_role_state") != "unknown":
        raise ValueError("returned allocation-pointer role state must be unknown")

    blockers = value.get("blockers")
    if not isinstance(blockers, list) or EXPECTED_BLOCKER not in blockers:
        raise ValueError("returned allocation-pointer semantic blocker is missing")

    raw = value.get("required_instruction_targets")
    if not isinstance(raw, list) or not raw:
        raise ValueError("returned allocation-pointer boundary has no instruction targets")
    targets: list[str] = []
    for item in raw:
        target = _norm(item)
        if target is None:
            raise ValueError(f"invalid instruction target: {item!r}")
        targets.append(target)
    if len(set(targets)) != len(targets):
        raise ValueError("returned allocation-pointer boundary has duplicate targets")
    if targets != sorted(targets):
        raise ValueError("returned allocation-pointer targets must be sorted")

    origins = value.get("return_origin_targets")
    if not isinstance(origins, list):
        raise ValueError("return_origin_targets must be a list")
    normalized_origins = [_norm(item) for item in origins]
    if any(item is None for item in normalized_origins):
        raise ValueError("invalid return-origin target")
    missing = [target for target in targets if target not in normalized_origins]
    if missing:
        raise ValueError(
            "instruction target outside return-origin frontier: " + ", ".join(missing)
        )
    return value, targets


def _clean_operand(value: str) -> str:
    value = SIZE_PREFIX.sub("", value.strip()).strip()
    return re.sub(r"\s+", " ", value).upper()


def _parse_immediate(value: str) -> int | None:
    token = _clean_operand(value)
    try:
        if token.startswith("0X"):
            return int(token, 16)
        if token.endswith("H") and re.fullmatch(r"[0-9A-F]+H", token):
            return int(token[:-1], 16)
        if re.fullmatch(r"-?[0-9]+", token):
            return int(token, 10)
    except ValueError:
        return None
    return None


def _pcode_opcodes(instruction: dict[str, Any]) -> set[str]:
    rows = instruction.get("pcode")
    if not isinstance(rows, list):
        raise ValueError(f"{instruction.get('address')}: pcode must be a list")
    result: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("opcode"), str):
            raise ValueError(f"{instruction.get('address')}: malformed pcode")
        result.add(row["opcode"].upper())
    return result


def _flows(instruction: dict[str, Any]) -> list[str]:
    rows = instruction.get("flows")
    if not isinstance(rows, list):
        raise ValueError(f"{instruction.get('address')}: flows must be a list")
    result: list[str] = []
    for item in rows:
        value = _norm(item)
        if value is None:
            raise ValueError(f"{instruction.get('address')}: invalid flow target {item!r}")
        result.append(value)
    return result


def _fallthrough(instruction: dict[str, Any]) -> str | None:
    raw = instruction.get("fallthrough")
    if raw is None:
        return None
    value = _norm(raw)
    if value is None:
        raise ValueError(f"{instruction.get('address')}: invalid fallthrough {raw!r}")
    return value


def _direct_target(instruction: dict[str, Any]) -> str | None:
    flows = _flows(instruction)
    return flows[0] if len(flows) == 1 else None


def _load_instruction_rows(path: Path, expected_targets: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict):
            raise ValueError(f"{path}: function metadata missing")
        address = _norm(function.get("address"))
        if address is None:
            raise ValueError(f"{path}: invalid function address")
        requested = _norm(row.get("requested"))
        if requested != address:
            raise ValueError(
                f"{path}: requested/function identity drift: {row.get('requested')!r} != {address}"
            )
        if address in result:
            raise ValueError(f"{path}: duplicate function {address}")
        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{address}: instructions missing")
        result[address] = row

    expected = set(expected_targets)
    actual = set(result)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            "instruction export target identity drift"
            + (f"; missing={missing}" if missing else "")
            + (f"; extra={extra}" if extra else "")
        )
    return result


def _instruction_map(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    instructions = row.get("instructions")
    if not isinstance(instructions, list) or not instructions:
        raise ValueError("instruction list missing")
    result: dict[str, dict[str, Any]] = {}
    for instruction in instructions:
        if not isinstance(instruction, dict):
            raise ValueError("invalid instruction row")
        address = _norm(instruction.get("address"))
        if address is None:
            raise ValueError("invalid instruction address")
        if address in result:
            raise ValueError(f"duplicate instruction {address}")
        _flows(instruction)
        _fallthrough(instruction)
        _pcode_opcodes(instruction)
        result[address] = instruction
    return result


def _eax_destination(operands: list[str]) -> str | None:
    if not operands:
        return None
    destination = _clean_operand(operands[0])
    if destination == "EAX" or destination in EAX_PARTIAL:
        return destination
    return None


def _transfer_origin(instruction: dict[str, Any], origin: Origin) -> Origin:
    address = _norm(instruction.get("address"))
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = [str(item) for item in (instruction.get("operands") or [])]
    opcodes = _pcode_opcodes(instruction)

    if mnemonic == "CALL":
        target = _direct_target(instruction)
        if target is None or "CALL" not in opcodes:
            return Origin(
                "ambiguous-call-result",
                target=target,
                instruction=address,
                detail="CALL lacks one exact direct flow and p-code CALL",
            )
        return Origin("direct-call-result", target=target, instruction=address)

    destination = _eax_destination(operands)
    if destination in EAX_PARTIAL:
        return Origin("partial-eax-write", instruction=address, detail=mnemonic)

    if mnemonic == "MOV" and destination == "EAX" and len(operands) == 2:
        source = _clean_operand(operands[1])
        if source == "EAX":
            return origin
        immediate = _parse_immediate(source)
        if immediate is not None:
            return Origin("constant", instruction=address, detail=f"0x{immediate & 0xffffffff:x}")
        if source in FULL_GPRS:
            return Origin("register-source", instruction=address, detail=source)
        if "[" in source and "]" in source:
            return Origin("memory-source", instruction=address, detail=source)
        return Origin("ambiguous-eax-write", instruction=address, detail=source)

    if mnemonic == "LEA" and destination == "EAX" and len(operands) == 2:
        return Origin("address-source", instruction=address, detail=_clean_operand(operands[1]))

    if mnemonic == "XOR" and destination == "EAX" and len(operands) == 2:
        if _clean_operand(operands[1]) == "EAX":
            return Origin("constant", instruction=address, detail="0x0")
        return Origin("derived-eax", instruction=address, detail=str(instruction.get("text") or mnemonic))

    if destination == "EAX":
        if mnemonic == "POP":
            return Origin("stack-source", instruction=address, detail="POP EAX")
        return Origin("derived-eax", instruction=address, detail=str(instruction.get("text") or mnemonic))

    if mnemonic in {"MUL", "DIV", "IDIV", "CPUID", "RDTSC", "RDTSCP"}:
        return Origin("implicit-eax-write", instruction=address, detail=mnemonic)
    if mnemonic == "IMUL" and len(operands) == 1:
        return Origin("implicit-eax-write", instruction=address, detail=mnemonic)
    if mnemonic in {"XCHG", "XADD"}:
        cleaned = [_clean_operand(item) for item in operands]
        if "EAX" in cleaned or any(item in EAX_PARTIAL for item in cleaned):
            return Origin("ambiguous-eax-write", instruction=address, detail=mnemonic)
    return origin


def _origin_machine_state(origin: Origin) -> str:
    if origin.kind in {
        "function-entry-eax",
        "direct-call-result",
        "constant",
        "register-source",
        "memory-source",
        "address-source",
    }:
        return "verified"
    return "ambiguous"


def _origin_payload(origin: Origin) -> dict[str, Any]:
    return {
        "kind": origin.kind,
        "target": origin.target,
        "instruction": origin.instruction,
        "detail": origin.detail,
    }


def _origin_sort_key(origin: Origin) -> tuple[str, str, str, str]:
    return tuple(value or "" for value in origin)


def _successors(instruction: dict[str, Any], known: set[str]) -> list[str]:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    flows = [target for target in _flows(instruction) if target in known]
    fallthrough = _fallthrough(instruction)
    if mnemonic.startswith("RET"):
        return []
    if mnemonic == "JMP":
        return flows
    if mnemonic.startswith("J"):
        result = list(flows)
        if fallthrough in known and fallthrough not in result:
            result.append(fallthrough)
        return result
    if fallthrough in known:
        return [fallthrough]
    return []


def _analyze_target(target: str, row: dict[str, Any]) -> dict[str, Any]:
    by_address = _instruction_map(row)
    known = set(by_address)
    if target not in known:
        raise ValueError(f"{target}: exact function entry instruction missing")
    entry = target

    queue: deque[tuple[str, Origin]] = deque([(entry, ENTRY_EAX)])
    seen: set[tuple[str, Origin]] = set()
    ret_origins: dict[str, set[Origin]] = defaultdict(set)
    tail_targets: dict[str, str] = {}
    blockers: list[dict[str, Any]] = []

    while queue:
        address, incoming = queue.popleft()
        state = (address, incoming)
        if state in seen:
            continue
        seen.add(state)
        instruction = by_address[address]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        opcodes = _pcode_opcodes(instruction)

        if mnemonic.startswith("RET"):
            if "RETURN" not in opcodes:
                blockers.append({"id": "ret-pcode-return-missing", "instruction": address})
            ret_origins[address].add(incoming)
            continue

        if mnemonic == "JMP":
            direct = _direct_target(instruction)
            branch_proven = "BRANCH" in opcodes
            if not branch_proven:
                blockers.append({"id": "jmp-pcode-branch-missing", "instruction": address})
            if direct is not None and direct not in known:
                if branch_proven:
                    tail_targets[address] = direct
                continue
            if direct is None:
                blockers.append({"id": "jmp-target-ambiguous", "instruction": address})
                continue

        if mnemonic.startswith("J") and mnemonic != "JMP" and "CBRANCH" not in opcodes:
            blockers.append({"id": "conditional-pcode-cbranch-missing", "instruction": address})

        outgoing = _transfer_origin(instruction, incoming)
        successors = _successors(instruction, known)
        if not successors and mnemonic not in {"JMP"}:
            blockers.append({"id": "reachable-path-has-no-successor-or-exit", "instruction": address})
        for successor in successors:
            queue.append((successor, outgoing))

    exits: list[dict[str, Any]] = []
    next_targets: set[str] = set()
    resolved = True

    for address in sorted(ret_origins):
        origins = ret_origins[address]
        if len(origins) != 1:
            resolved = False
            exits.append(
                {
                    "kind": "ret",
                    "instruction": address,
                    "machine_return_origin_state": "ambiguous",
                    "origins": [
                        _origin_payload(item)
                        for item in sorted(origins, key=_origin_sort_key)
                    ],
                }
            )
            continue
        origin = next(iter(origins))
        state = _origin_machine_state(origin)
        if state != "verified":
            resolved = False
        if state == "verified" and origin.kind == "direct-call-result" and origin.target:
            next_targets.add(origin.target)
        exits.append(
            {
                "kind": "ret",
                "instruction": address,
                "machine_return_origin_state": state,
                "origin": _origin_payload(origin),
            }
        )

    for address in sorted(tail_targets):
        tail = tail_targets[address]
        next_targets.add(tail)
        exits.append(
            {
                "kind": "external-tail-transfer",
                "instruction": address,
                "machine_return_origin_state": "verified",
                "target": tail,
            }
        )

    if not exits:
        resolved = False
        blockers.append({"id": "no-reachable-return-or-tail-exit", "target": target})
    if blockers:
        resolved = False
    if not resolved:
        next_targets.clear()

    return {
        "address": target,
        "reachable_state_count": len(seen),
        "exit_count": len(exits),
        "exits": exits,
        "machine_return_origins_resolved": resolved,
        "next_return_origin_targets": sorted(next_targets),
        "returned_allocation_pointer_role_state": "unknown",
        "returned_allocation_pointer_role_proven": False,
        "blockers": blockers,
    }


def analyze_vehicle_returned_allocation_pointer_return_provenance(
    boundary_path: Path,
    instruction_jsonl: Path,
) -> dict[str, Any]:
    boundary, targets = _load_boundary(boundary_path)
    rows = _load_instruction_rows(instruction_jsonl, targets)

    analyses = [_analyze_target(target, rows[target]) for target in targets]
    all_resolved = all(item["machine_return_origins_resolved"] for item in analyses)
    next_targets = sorted(
        {
            target
            for item in analyses
            for target in item["next_return_origin_targets"]
        }
    )

    blockers: list[str] = []
    if not all_resolved:
        blockers.append("target_machine_return_origin_not_fully_resolved")
    blockers.append(EXPECTED_BLOCKER)
    if all_resolved and not next_targets:
        blockers.append("returned_pointer_semantics_require_non_call_origin_interpretation")

    contexts = boundary.get("vehicle_create_bridges")
    if not isinstance(contexts, list):
        raise ValueError("vehicle_create_bridges must be a list")

    joined_contexts: list[dict[str, Any]] = []
    for context in contexts:
        if not isinstance(context, dict):
            raise ValueError("invalid vehicle_create_bridges row")
        row = dict(context)
        row.update(
            {
                "returned_pointer_target_machine_return_origins_resolved": all_resolved,
                "returned_pointer_next_return_origin_targets": next_targets,
                "returned_allocation_pointer_role_state": "unknown",
                "returned_allocation_pointer_role_proven": False,
            }
        )
        joined_contexts.append(row)

    return {
        "format": FORMAT,
        "input_boundary": str(boundary_path),
        "instruction_export": str(instruction_jsonl),
        "analyzed_target_count": len(analyses),
        "required_instruction_targets": targets,
        "targets": analyses,
        "all_target_machine_return_origins_resolved": all_resolved,
        "next_return_origin_target_count": len(next_targets),
        "next_return_origin_targets": next_targets,
        "vehicle_create_bridges": joined_contexts,
        "returned_allocation_pointer_role_state": "unknown",
        "returned_allocation_pointer_role_proven": False,
        "blockers": blockers,
        "scope": {
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "machine_return_origin_is_semantic_role": False,
            "callgraph_adjacency_is_semantic_role": False,
            "returned_allocation_pointer_role_proven": False,
            "note": (
                "This stage advances exact machine EAX provenance only. A direct CALL result "
                "or tail target is a next static frontier, not proof that the value is an "
                "allocated pointer."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("boundary", type=Path)
    parser.add_argument("instructions", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_vehicle_returned_allocation_pointer_return_provenance(
        args.boundary,
        args.instructions,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

    print(f"targets: {report['analyzed_target_count']}")
    print(f"machine origins resolved: {report['all_target_machine_return_origins_resolved']}")
    print(f"next return-origin targets: {report['next_return_origin_target_count']}")
    print(f"returned allocation-pointer role: {report['returned_allocation_pointer_role_state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

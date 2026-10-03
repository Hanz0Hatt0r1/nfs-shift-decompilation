#!/usr/bin/env python3
"""Audit exact inner target return origins for the vehicle allocation-pointer boundary.

The semantic boundary publishes a finite list of local functions whose machine
return values must be understood before an allocated-pointer role can be proven.
This analyzer consumes a targeted `SHIFT.GhidraFunctionInstructions/2` export for
exactly those functions, explores every reachable RET/external tail exit, and
tracks the immediate EAX origin through a conservative x86 subset.

It emits the next finite direct-CALL/tail target frontier.  Machine provenance is
not promoted to allocation-pointer, allocator ABI, operator-new, ownership,
constructor or whole-runtime-object semantics.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, NamedTuple

FORMAT = "SHIFT.VehicleReturnedAllocationPointerTargetReturnAudit/1"
BOUNDARY_FORMAT = "SHIFT.VehicleReturnedAllocationPointerBoundary/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
EXPECTED_BLOCKER = "returned_allocation_pointer_semantic_role_not_proven"

FULL_GPRS = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
PARTIAL_EAX = {"AX", "AL", "AH"}
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


def _load_boundary(path: Path) -> tuple[dict[str, Any], list[str]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != BOUNDARY_FORMAT:
        raise ValueError(f"{path}: expected {BOUNDARY_FORMAT}")
    if value.get("returned_allocation_pointer_role_state") != "unknown":
        raise ValueError("returned allocation-pointer semantic state must be unknown")
    if value.get("returned_allocation_pointer_role_proven") is not False:
        raise ValueError("returned allocation-pointer role must remain unproven")
    blockers = value.get("blockers")
    if not isinstance(blockers, list) or EXPECTED_BLOCKER not in blockers:
        raise ValueError("semantic boundary is missing the return-role blocker")

    raw = value.get("required_instruction_targets")
    if not isinstance(raw, list) or not raw:
        raise ValueError("semantic boundary has no required instruction targets")
    targets: list[str] = []
    for item in raw:
        address = _norm(item)
        if address is None:
            raise ValueError(f"invalid required instruction target: {item!r}")
        targets.append(address)
    if len(set(targets)) != len(targets):
        raise ValueError("semantic boundary contains duplicate instruction targets")
    if targets != sorted(targets):
        raise ValueError("semantic boundary instruction targets must be sorted")
    return value, targets


def _load_instruction_rows(path: Path, targets: list[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved requested function {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict):
            raise ValueError(f"{path}: function metadata missing")
        address = _norm(function.get("address"))
        if address is None:
            raise ValueError(f"{path}: invalid function address")
        if address in rows:
            raise ValueError(f"{path}: duplicate function row {address}")
        rows[address] = row

    target_set = set(targets)
    missing = sorted(target_set - set(rows))
    extra = sorted(set(rows) - target_set)
    if missing:
        raise ValueError("instruction export missing boundary target(s): " + ", ".join(missing))
    if extra:
        raise ValueError("instruction export contains non-boundary target(s): " + ", ".join(extra))
    return rows


def _flows(instruction: dict[str, Any]) -> list[str]:
    values = instruction.get("flows")
    if not isinstance(values, list):
        raise ValueError(f"{instruction.get('address')}: flows must be a list")
    return [address for item in values if (address := _norm(item)) is not None]


def _pcode(instruction: dict[str, Any]) -> set[str]:
    rows = instruction.get("pcode")
    if not isinstance(rows, list):
        raise ValueError(f"{instruction.get('address')}: pcode must be a list")
    result: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("opcode"), str):
            raise ValueError(f"{instruction.get('address')}: malformed pcode row")
        result.add(row["opcode"].upper())
    return result


def _direct_target(instruction: dict[str, Any]) -> str | None:
    flows = _flows(instruction)
    return flows[0] if len(flows) == 1 else None


def _instruction_map(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = row.get("instructions")
    if not isinstance(raw, list) or not raw:
        raise ValueError("target instruction list missing")
    result: dict[str, dict[str, Any]] = {}
    for instruction in raw:
        if not isinstance(instruction, dict):
            raise ValueError("invalid target instruction row")
        address = _norm(instruction.get("address"))
        if address is None:
            raise ValueError("invalid target instruction address")
        if address in result:
            raise ValueError(f"duplicate target instruction {address}")
        _flows(instruction)
        _pcode(instruction)
        result[address] = instruction
    return result


def _origin_payload(origin: Origin) -> dict[str, Any]:
    return {
        "kind": origin.kind,
        "target": origin.target,
        "instruction": origin.instruction,
        "detail": origin.detail,
    }


def _resolved_origin(origin: Origin) -> bool:
    return origin.kind in {
        "function-entry-eax",
        "direct-call-result",
        "constant",
        "register-source",
        "memory-source",
        "address-source",
    }


def _transfer_eax(instruction: dict[str, Any], origin: Origin) -> Origin:
    address = _norm(instruction.get("address"))
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = [str(item) for item in (instruction.get("operands") or [])]
    opcodes = _pcode(instruction)

    if mnemonic == "CALL":
        target = _direct_target(instruction)
        if target is None or "CALL" not in opcodes:
            return Origin(
                "ambiguous-call-result",
                target=target,
                instruction=address,
                detail="CALL lacks one exact flow and p-code CALL",
            )
        return Origin("direct-call-result", target=target, instruction=address)

    destination = _clean_operand(operands[0]) if operands else None
    if destination in PARTIAL_EAX:
        return Origin(
            "partial-eax-write",
            instruction=address,
            detail=str(instruction.get("text") or mnemonic),
        )

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
        return Origin("derived-eax", instruction=address, detail=str(instruction.get("text")))

    if destination == "EAX":
        if mnemonic == "POP":
            return Origin("stack-source", instruction=address, detail="POP EAX")
        return Origin("derived-eax", instruction=address, detail=str(instruction.get("text") or mnemonic))

    if mnemonic in {"MUL", "DIV", "IDIV", "CPUID", "RDTSC", "RDTSCP"}:
        return Origin("implicit-eax-write", instruction=address, detail=str(instruction.get("text") or mnemonic))
    if mnemonic == "IMUL" and len(operands) == 1:
        return Origin("implicit-eax-write", instruction=address, detail=str(instruction.get("text") or mnemonic))
    if mnemonic in {"XCHG", "XADD"}:
        cleaned = [_clean_operand(item) for item in operands]
        if "EAX" in cleaned or any(item in PARTIAL_EAX for item in cleaned):
            return Origin("ambiguous-eax-write", instruction=address, detail=str(instruction.get("text") or mnemonic))
    return origin


def _internal_successors(
    instruction: dict[str, Any],
    known: set[str],
) -> list[str]:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    flows = [target for target in _flows(instruction) if target in known]
    fallthrough = _norm(instruction.get("fallthrough"))
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


def _analyze_target(address: str, row: dict[str, Any]) -> dict[str, Any]:
    by_address = _instruction_map(row)
    known = set(by_address)
    ordered = sorted(known, key=lambda item: int(item, 16))
    entry = address if address in known else ordered[0]

    queue: deque[tuple[str, Origin]] = deque([(entry, ENTRY_EAX)])
    seen: set[tuple[str, Origin]] = set()
    ret_origins: dict[str, set[Origin]] = defaultdict(set)
    tails: dict[str, set[tuple[str | None, bool]]] = defaultdict(set)
    blockers: list[dict[str, Any]] = []
    max_iterations = max(512, len(by_address) * 96)
    iterations = 0

    while queue:
        iterations += 1
        if iterations > max_iterations:
            raise ValueError(f"{address}: return-origin analysis iteration limit reached")
        instruction_address, origin = queue.popleft()
        key = instruction_address, origin
        if key in seen:
            continue
        seen.add(key)
        instruction = by_address[instruction_address]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        opcodes = _pcode(instruction)

        if mnemonic.startswith("RET"):
            if "RETURN" not in opcodes:
                blockers.append(
                    {
                        "id": "ret-without-return-pcode",
                        "instruction": instruction_address,
                        "evidence_state": "ambiguous",
                    }
                )
            ret_origins[instruction_address].add(origin)
            continue

        if mnemonic == "JMP":
            target = _direct_target(instruction)
            if target in known:
                if "BRANCH" not in opcodes:
                    blockers.append(
                        {
                            "id": "internal-jmp-without-branch-pcode",
                            "instruction": instruction_address,
                            "target": target,
                            "evidence_state": "ambiguous",
                        }
                    )
                queue.append((target, origin))
                continue
            branch_ok = target is not None and "BRANCH" in opcodes
            tails[instruction_address].add((target, branch_ok))
            if not branch_ok:
                blockers.append(
                    {
                        "id": "external-tail-not-exact-direct-branch",
                        "instruction": instruction_address,
                        "target": target,
                        "evidence_state": "ambiguous",
                    }
                )
            continue

        if mnemonic.startswith("J") and "CBRANCH" not in opcodes:
            blockers.append(
                {
                    "id": "conditional-branch-without-cbranch-pcode",
                    "instruction": instruction_address,
                    "evidence_state": "ambiguous",
                }
            )

        next_origin = _transfer_eax(instruction, origin)
        successors = _internal_successors(instruction, known)
        if not successors:
            blockers.append(
                {
                    "id": "reachable-nonexit-terminal",
                    "instruction": instruction_address,
                    "mnemonic": mnemonic,
                    "evidence_state": "unknown",
                }
            )
            continue
        for successor in successors:
            queue.append((successor, next_origin))

    exits: list[dict[str, Any]] = []
    next_targets: set[str] = set()
    terminal_origins: list[dict[str, Any]] = []

    for instruction_address in sorted(ret_origins, key=lambda item: int(item, 16)):
        origins = sorted(
            ret_origins[instruction_address],
            key=lambda item: (item.kind, item.target or "", item.instruction or "", item.detail or ""),
        )
        state = "verified" if len(origins) == 1 and _resolved_origin(origins[0]) else "ambiguous"
        if state != "verified":
            blockers.append(
                {
                    "id": "ret-eax-origin-not-unique-and-resolved",
                    "instruction": instruction_address,
                    "origin_count": len(origins),
                    "evidence_state": "ambiguous",
                }
            )
        if state == "verified":
            origin = origins[0]
            if origin.kind == "direct-call-result" and origin.target:
                next_targets.add(origin.target)
            else:
                terminal_origins.append(_origin_payload(origin))
        exits.append(
            {
                "kind": "ret",
                "instruction": instruction_address,
                "machine_return_origin_state": state,
                "eax_origins": [_origin_payload(item) for item in origins],
                "unique_eax_origin": _origin_payload(origins[0]) if len(origins) == 1 else None,
                "returned_allocation_pointer_role_proven": False,
            }
        )

    for instruction_address in sorted(tails, key=lambda item: int(item, 16)):
        candidates = sorted(tails[instruction_address], key=lambda item: (item[0] or "", item[1]))
        state = "verified" if len(candidates) == 1 and candidates[0][0] and candidates[0][1] else "ambiguous"
        target = candidates[0][0] if len(candidates) == 1 else None
        if state == "verified" and target:
            next_targets.add(target)
        exits.append(
            {
                "kind": "external-tail-transfer",
                "instruction": instruction_address,
                "target": target,
                "machine_return_origin_state": state,
                "tail_candidates": [
                    {"target": candidate, "direct_branch_pcode_verified": ok}
                    for candidate, ok in candidates
                ],
                "returned_allocation_pointer_role_proven": False,
            }
        )

    exits.sort(key=lambda item: (int(str(item["instruction"]), 16), item["kind"]))
    if not exits:
        blockers.append({"id": "no-reachable-return-or-tail-exit", "evidence_state": "unknown"})

    all_resolved = bool(exits) and not blockers and all(
        item.get("machine_return_origin_state") == "verified" for item in exits
    )
    function = row.get("function") or {}
    return {
        "address": address,
        "name": function.get("name"),
        "calling_convention": function.get("calling_convention"),
        "reachable_state_count": len(seen),
        "exit_count": len(exits),
        "exits": exits,
        "machine_return_origins_resolved": all_resolved,
        "next_return_targets": sorted(next_targets),
        "terminal_machine_origins": terminal_origins,
        "blockers": blockers,
        "returned_allocation_pointer_role_state": "unknown",
        "returned_allocation_pointer_role_proven": False,
    }


def analyze_vehicle_returned_allocation_pointer_target_returns(
    boundary_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    boundary, targets = _load_boundary(boundary_path)
    rows = _load_instruction_rows(instruction_export_path, targets)
    analyses = [_analyze_target(address, rows[address]) for address in targets]

    all_resolved = all(row["machine_return_origins_resolved"] is True for row in analyses)
    next_targets = sorted(
        {
            target
            for row in analyses
            for target in row.get("next_return_targets") or []
            if isinstance(target, str)
        }
    )
    cycles = sorted(set(next_targets) & set(targets))
    blockers = [
        {"target": row["address"], **blocker}
        for row in analyses
        for blocker in row.get("blockers") or []
    ]
    if cycles:
        blockers.extend(
            {
                "target": address,
                "id": "return-origin-cycle-to-current-target",
                "evidence_state": "ambiguous",
            }
            for address in cycles
        )
        all_resolved = False

    if not next_targets:
        blockers.append(
            {
                "id": "no-further-call-or-tail-targets",
                "evidence_state": "unknown",
                "note": "machine origin terminates locally but return semantics are still unproven",
            }
        )

    contexts = boundary.get("vehicle_create_bridges")
    if not isinstance(contexts, list):
        raise ValueError("semantic boundary vehicle_create_bridges must be a list")
    joined_contexts: list[dict[str, Any]] = []
    for row in contexts:
        if not isinstance(row, dict):
            raise ValueError("semantic boundary contains invalid vehicle context")
        joined = dict(row)
        joined["returned_pointer_target_return_audit_state"] = (
            "verified" if all_resolved else "ambiguous"
        )
        joined["returned_pointer_next_instruction_targets"] = list(next_targets)
        joined["returned_allocation_pointer_role_state"] = "unknown"
        joined["returned_allocation_pointer_role_proven"] = False
        joined_contexts.append(joined)

    return {
        "format": FORMAT,
        "inputs": {
            "semantic_boundary": str(boundary_path),
            "instruction_export": str(instruction_export_path),
        },
        "target_count": len(analyses),
        "verified_target_return_origin_count": sum(
            row["machine_return_origins_resolved"] is True for row in analyses
        ),
        "all_target_machine_return_origins_resolved": all_resolved,
        "targets": analyses,
        "next_instruction_target_count": len(next_targets),
        "next_instruction_targets": next_targets,
        "return_origin_cycles": cycles,
        "returned_allocation_pointer_role_state": "unknown",
        "returned_allocation_pointer_role_proven": False,
        "vehicle_create_bridges": joined_contexts,
        "blockers": blockers,
        "scope": {
            "all_reachable_target_exits_examined": True,
            "direct_call_result_origin_can_be_verified": True,
            "external_tail_origin_can_be_verified": True,
            "terminal_local_origin_is_semantic_proof": False,
            "recursive_target_selection_ranked": False,
            "returned_allocation_pointer_role_proven": False,
            "allocator_abi_proven": False,
            "operator_new_identity_proven": False,
            "object_size_proven": False,
            "constructor_semantics_proven": False,
            "ownership_semantics_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
            "note": (
                "This audit recursively narrows machine origins of the exact inner target "
                "returns. A direct CALL result, constant, memory source or tail target does "
                "not by itself establish allocated-pointer semantics."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("boundary", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = analyze_vehicle_returned_allocation_pointer_target_returns(
        args.boundary,
        args.instruction_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["next_instruction_targets"]),
            encoding="utf-8",
        )

    print(f"format: {report['format']}")
    print(f"targets audited: {report['target_count']}")
    print(
        "resolved machine return origins: "
        f"{report['verified_target_return_origin_count']}/{report['target_count']}"
    )
    print(f"next instruction targets: {report['next_instruction_target_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"target list: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

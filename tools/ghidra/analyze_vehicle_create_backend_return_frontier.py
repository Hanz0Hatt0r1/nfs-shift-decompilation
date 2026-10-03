#!/usr/bin/env python3
"""Recover a fail-closed machine return-origin frontier for vehicle create backends.

This stage consumes the proven create-helper exit provenance and reopens the two
retail create backends selected by that evidence:

- FUN_00638020 (allocation-diagnostic-backend)
- FUN_006382b0 (create-fallback-backend)

For every reachable RET or external tail transfer it records the exact immediate
machine origin of the backend exit value/control.  A direct CALL result reaching
EAX, a constant written to EAX, an entry-register value, or an exact external
JMP target can therefore be represented without assigning allocator semantics.

The output intentionally does *not* claim that any returned EAX is an allocated
pointer, that either backend is language-level operator new, that an allocation
request equals object size, or that the returned value is the same runtime
object later observed on the vehicle update path.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, NamedTuple

FORMAT = "SHIFT.VehicleCreateBackendReturnOriginFrontier/1"
UPSTREAM_FORMAT = "SHIFT.VehicleCreateHelperReturnProvenance/1"
BACKEND_FORMAT = "SHIFT-MEMORY-BACKEND-EVIDENCE/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"

ALLOCATION_BACKEND = "0x00638020"
FALLBACK_BACKEND = "0x006382b0"
EXPECTED_BACKENDS: dict[str, str] = {
    ALLOCATION_BACKEND: "allocation-diagnostic-backend",
    FALLBACK_BACKEND: "create-fallback-backend",
}

FULL_GPRS = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
EAX_PARTIAL = {"AX", "AL", "AH"}
SIZE_PREFIX = re.compile(r"^(?:BYTE|WORD|DWORD|QWORD)\s+PTR\s+", re.IGNORECASE)


class Origin(NamedTuple):
    kind: str
    target: str | None = None
    instruction: str | None = None
    detail: str | None = None


ENTRY_EAX = Origin("function-entry-eax")


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
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
    address = instruction.get("address")
    rows = instruction.get("pcode")
    if not isinstance(rows, list):
        raise ValueError(f"{address}: pcode must be a list")
    result: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("opcode"), str):
            raise ValueError(f"{address}: malformed pcode operation")
        result.add(row["opcode"].upper())
    return result


def _flows(instruction: dict[str, Any]) -> list[str]:
    values = instruction.get("flows")
    if not isinstance(values, list):
        raise ValueError(f"{instruction.get('address')}: flows must be a list")
    return [value for item in values if (value := _norm(item)) is not None]


def _fallthrough(instruction: dict[str, Any]) -> str | None:
    return _norm(instruction.get("fallthrough"))


def _direct_target(instruction: dict[str, Any]) -> str | None:
    flows = _flows(instruction)
    return flows[0] if len(flows) == 1 else None


def _upstream_context(report: dict[str, Any]) -> list[dict[str, Any]]:
    if report.get("all_reachable_helper_exits_backend_sourced") is not True:
        raise ValueError("create-helper return provenance is not fully backend-sourced")

    exits = report.get("exits")
    if not isinstance(exits, list):
        raise ValueError("create-helper return provenance exits must be a list")
    verified_targets = {
        target
        for row in exits
        if isinstance(row, dict)
        and row.get("machine_exit_provenance_state") == "verified"
        and (target := _norm(row.get("backend_target"))) in EXPECTED_BACKENDS
    }
    missing = sorted(set(EXPECTED_BACKENDS) - verified_targets)
    if missing:
        raise ValueError(
            "create-helper return provenance is missing verified backend exit(s): "
            + ", ".join(missing)
        )

    rows = report.get("vehicle_create_bridges")
    if not isinstance(rows, list) or not rows:
        raise ValueError("create-helper return provenance vehicle_create_bridges missing")
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("create-helper return provenance contains invalid bridge row")
        if row.get("helper_machine_exit_provenance_state") != "verified":
            raise ValueError("vehicle create bridge helper machine exit provenance is not verified")
        result.append(row)
    return result


def _backend_roles(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = report.get("functions")
    if not isinstance(rows, list):
        raise ValueError("memory backend evidence functions must be a list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("memory backend evidence contains invalid function row")
        address = _norm(row.get("address"))
        if address is None:
            continue
        if address in result:
            raise ValueError(f"memory backend evidence duplicate target {address}")
        result[address] = row

    missing = sorted(set(EXPECTED_BACKENDS) - set(result))
    if missing:
        raise ValueError("memory backend evidence missing create backend(s): " + ", ".join(missing))
    for address, expected_role in EXPECTED_BACKENDS.items():
        if result[address].get("role") != expected_role:
            raise ValueError(
                f"{address}: backend role drift: expected {expected_role}, "
                f"got {result[address].get('role')!r}"
            )
    return result


def _load_instruction_rows(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    seen_any = False
    for row in _read_jsonl(path):
        seen_any = True
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
        if address in result:
            raise ValueError(f"{path}: duplicate function {address}")
        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{address}: instructions missing")
        result[address] = row
    if not seen_any:
        raise ValueError(f"{path}: empty instruction export")
    missing = sorted(set(EXPECTED_BACKENDS) - set(result))
    if missing:
        raise ValueError("instruction export missing create backend(s): " + ", ".join(missing))
    return result


def _instruction_map(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = row.get("instructions")
    if not isinstance(values, list) or not values:
        raise ValueError("backend instruction list missing")
    result: dict[str, dict[str, Any]] = {}
    for instruction in values:
        if not isinstance(instruction, dict):
            raise ValueError("invalid backend instruction row")
        address = _norm(instruction.get("address"))
        if address is None:
            raise ValueError("invalid backend instruction address")
        if address in result:
            raise ValueError(f"duplicate backend instruction {address}")
        # Validate structural fields up front so format drift cannot be hidden on
        # a path that happens not to be visited by the current CFG traversal.
        _flows(instruction)
        _pcode_opcodes(instruction)
        result[address] = instruction
    return result


def _origin_payload(origin: Origin) -> dict[str, Any]:
    return {
        "kind": origin.kind,
        "target": origin.target,
        "instruction": origin.instruction,
        "detail": origin.detail,
    }


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
    operands = [str(value) for value in (instruction.get("operands") or [])]
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
            return Origin(
                "constant",
                instruction=address,
                detail=f"0x{immediate & 0xffffffff:x}",
            )
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
        if mnemonic in {
            "MOVZX", "MOVSX", "ADD", "ADC", "SUB", "SBB", "AND", "OR", "INC",
            "DEC", "NEG", "NOT", "SHL", "SHR", "SAR", "ROL", "ROR", "BSWAP",
            "IMUL",
        }:
            return Origin("derived-eax", instruction=address, detail=str(instruction.get("text")))
        return Origin(
            "ambiguous-eax-write",
            instruction=address,
            detail=str(instruction.get("text") or mnemonic),
        )

    if mnemonic in {"MUL", "DIV", "IDIV", "CPUID", "RDTSC", "RDTSCP"}:
        return Origin(
            "implicit-eax-write",
            instruction=address,
            detail=str(instruction.get("text") or mnemonic),
        )
    if mnemonic == "IMUL" and len(operands) == 1:
        return Origin(
            "implicit-eax-write",
            instruction=address,
            detail=str(instruction.get("text") or mnemonic),
        )
    if mnemonic in {"XCHG", "XADD"}:
        cleaned = [_clean_operand(value) for value in operands]
        if "EAX" in cleaned or any(value in EAX_PARTIAL for value in cleaned):
            return Origin(
                "ambiguous-eax-write",
                instruction=address,
                detail=str(instruction.get("text") or mnemonic),
            )
    return origin


def _internal_successors(
    instruction: dict[str, Any],
    known: set[str],
) -> list[str]:
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


def _analyze_backend(
    address: str,
    role_row: dict[str, Any],
    instruction_row: dict[str, Any],
) -> dict[str, Any]:
    by_address = _instruction_map(instruction_row)
    known = set(by_address)
    ordered = sorted(known, key=lambda value: int(value, 16))
    entry = address if address in known else ordered[0]

    queue: deque[tuple[str, Origin]] = deque([(entry, ENTRY_EAX)])
    seen: set[tuple[str, Origin]] = set()
    ret_origins: dict[str, set[Origin]] = defaultdict(set)
    tail_targets: dict[str, set[tuple[str | None, bool]]] = defaultdict(set)
    blockers: list[dict[str, Any]] = []
    iterations = 0
    max_iterations = max(512, len(by_address) * 96)

    while queue:
        iterations += 1
        if iterations > max_iterations:
            raise ValueError(f"{address}: control-flow analysis iteration limit reached")
        instruction_address, origin = queue.popleft()
        state_key = instruction_address, origin
        if state_key in seen:
            continue
        seen.add(state_key)
        instruction = by_address[instruction_address]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        opcodes = _pcode_opcodes(instruction)

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
            tail_targets[instruction_address].add((target, branch_ok))
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

        if mnemonic.startswith("J"):
            if "CBRANCH" not in opcodes:
                blockers.append(
                    {
                        "id": "conditional-branch-without-cbranch-pcode",
                        "instruction": instruction_address,
                        "evidence_state": "ambiguous",
                    }
                )

        next_origin = _transfer_origin(instruction, origin)
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

    for instruction_address in sorted(ret_origins, key=lambda value: int(value, 16)):
        origins = sorted(
            ret_origins[instruction_address],
            key=lambda value: (value.kind, value.target or "", value.instruction or "", value.detail or ""),
        )
        states = {_origin_machine_state(origin) for origin in origins}
        state = "verified" if len(origins) == 1 and states == {"verified"} else "ambiguous"
        if state != "verified":
            blockers.append(
                {
                    "id": "ret-eax-origin-not-unique-and-resolved",
                    "instruction": instruction_address,
                    "origin_count": len(origins),
                    "evidence_state": "ambiguous",
                }
            )
        if state == "verified" and origins[0].kind == "direct-call-result" and origins[0].target:
            next_targets.add(origins[0].target)
        exits.append(
            {
                "kind": "ret",
                "instruction": instruction_address,
                "machine_return_origin_state": state,
                "eax_origins": [_origin_payload(origin) for origin in origins],
                "unique_eax_origin": _origin_payload(origins[0]) if len(origins) == 1 else None,
                "allocated_pointer_return_proven": False,
            }
        )

    for instruction_address in sorted(tail_targets, key=lambda value: int(value, 16)):
        rows = sorted(tail_targets[instruction_address], key=lambda value: (value[0] or "", value[1]))
        state = "verified" if len(rows) == 1 and rows[0][0] is not None and rows[0][1] else "ambiguous"
        target = rows[0][0] if len(rows) == 1 else None
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
                    for candidate, ok in rows
                ],
                "allocated_pointer_return_proven": False,
            }
        )

    exits.sort(key=lambda row: (int(str(row["instruction"]), 16), str(row["kind"])))
    if not exits:
        blockers.append(
            {
                "id": "no-reachable-return-or-tail-exit",
                "evidence_state": "unknown",
            }
        )

    all_resolved = bool(exits) and all(
        row.get("machine_return_origin_state") == "verified" for row in exits
    ) and not blockers
    function = instruction_row.get("function") or {}
    return {
        "address": address,
        "name": function.get("name") or role_row.get("name"),
        "role": role_row.get("role"),
        "calling_convention": function.get("calling_convention") or role_row.get("calling_convention"),
        "reachable_state_count": len(seen),
        "exit_count": len(exits),
        "exits": exits,
        "machine_return_origins_resolved": all_resolved,
        "next_return_origin_targets": sorted(next_targets),
        "blockers": blockers,
        "return_value_semantics_state": "unknown",
        "allocated_pointer_return_proven": False,
    }


def analyze_vehicle_create_backend_return_frontier(
    upstream_path: Path,
    backend_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    upstream = _load(upstream_path, UPSTREAM_FORMAT)
    backend = _load(backend_path, BACKEND_FORMAT)
    contexts = _upstream_context(upstream)
    roles = _backend_roles(backend)
    instruction_rows = _load_instruction_rows(instruction_export_path)

    backends = [
        _analyze_backend(address, roles[address], instruction_rows[address])
        for address in EXPECTED_BACKENDS
    ]
    all_resolved = all(row["machine_return_origins_resolved"] is True for row in backends)
    next_targets = sorted(
        {
            target
            for row in backends
            for target in row.get("next_return_origin_targets") or []
            if isinstance(target, str)
        }
    )
    blockers = [
        {"backend": row["address"], **blocker}
        for row in backends
        for blocker in row.get("blockers") or []
    ]

    joined_contexts: list[dict[str, Any]] = []
    frontier_state = "verified" if all_resolved else "ambiguous"
    for row in contexts:
        joined = dict(row)
        joined["create_backend_return_frontier_state"] = frontier_state
        joined["create_backend_return_targets"] = list(next_targets)
        joined["backend_return_value_semantics_state"] = "unknown"
        joined["helper_return_is_allocated_pointer_proven"] = False
        joined["object_size_proven"] = False
        joined["same_runtime_object_as_vehicle_update_proven"] = False
        joined_contexts.append(joined)

    return {
        "format": FORMAT,
        "inputs": {
            "create_helper_return_provenance": str(upstream_path),
            "memory_backend_evidence": str(backend_path),
            "backend_instruction_export": str(instruction_export_path),
        },
        "backend_count": len(backends),
        "verified_backend_return_origin_count": sum(
            row["machine_return_origins_resolved"] is True for row in backends
        ),
        "all_backend_machine_return_origins_resolved": all_resolved,
        "backends": backends,
        "next_backend_return_target_count": len(next_targets),
        "next_backend_return_targets": next_targets,
        "vehicle_create_bridges": joined_contexts,
        "blockers": blockers,
        "scope": {
            "all_reachable_backend_exits_examined": True,
            "direct_call_result_eax_origin_can_be_verified": True,
            "external_tail_target_can_be_verified": True,
            "backend_machine_return_origin_frontier_verified": all_resolved,
            "backend_return_value_semantics_proven": False,
            "allocated_pointer_return_proven": False,
            "allocator_abi_proven": False,
            "operator_new_identity_proven": False,
            "object_size_proven": False,
            "constructor_semantics_proven": False,
            "ownership_semantics_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
            "note": (
                "This report identifies only immediate machine origins of the two create-backend "
                "exit values/control transfers. A CALL result in EAX or an exact tail target does "
                "not prove that the value is an allocated object pointer or establish allocator, "
                "operator-new, constructor, ownership, object-size, or whole-lifetime identity."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("create_helper_return_provenance", type=Path)
    parser.add_argument("memory_backend_evidence", type=Path)
    parser.add_argument("backend_instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_vehicle_create_backend_return_frontier(
        args.create_helper_return_provenance,
        args.memory_backend_evidence,
        args.backend_instruction_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"backends: {report['backend_count']}")
    print(
        "machine return origins resolved: "
        f"{report['verified_backend_return_origin_count']}/{report['backend_count']}"
    )
    print(f"next backend return targets: {report['next_backend_return_target_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

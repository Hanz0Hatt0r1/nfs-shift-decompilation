#!/usr/bin/env python3
"""Prove machine return provenance for vehicle create-side memory helpers.

The analyzer joins the vehicle lifetime/memory bridge to existing retail memory
wrapper forwarding and backend evidence, then reopens a targeted
SHIFT.GhidraFunctionInstructions/2 slice for the selected create helper.

It proves only where the helper's machine exit value/control comes from.  A
backend CALL result reaching RET, or an exact backend tail JMP, is not promoted
to allocated-pointer, operator-new, object-size, ownership, constructor, or
same-runtime-object semantics.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.VehicleCreateHelperReturnProvenance/1"
BRIDGE_FORMAT = "SHIFT.VehicleLifetimeMemoryBridge/1"
FORWARDING_FORMAT = "SHIFT-MEMORY-WRAPPER-FORWARDING/1"
BACKEND_FORMAT = "SHIFT-MEMORY-BACKEND-EVIDENCE/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"

CREATE_HELPER = "0x00886900"
ALLOCATION_BACKEND = "0x00638020"
FALLBACK_BACKEND = "0x006382b0"
EXPECTED_BACKENDS = {ALLOCATION_BACKEND, FALLBACK_BACKEND}


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


def _load_instruction_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    seen = False
    for row in _read_jsonl(path):
        seen = True
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
        if address in rows:
            raise ValueError(f"{path}: duplicate function {address}")
        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{address}: instructions missing")
        rows[address] = row
    if not seen:
        raise ValueError(f"{path}: empty instruction export")
    return rows


def _bridge_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = report.get("create_bridges")
    if not isinstance(rows, list):
        raise ValueError("lifetime memory bridge create_bridges must be a list")
    selected = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("lifetime memory bridge contains invalid create row")
        helper = _norm(row.get("preinitializer_helper"))
        if helper == CREATE_HELPER:
            selected.append(row)
    if not selected:
        raise ValueError(f"lifetime memory bridge has no {CREATE_HELPER} create row")
    return selected


def _forwarding_wrapper(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("wrappers")
    if not isinstance(rows, list):
        raise ValueError("memory forwarding wrappers must be a list")
    matches = [
        row for row in rows
        if isinstance(row, dict) and _norm(row.get("address")) == CREATE_HELPER
    ]
    if len(matches) != 1:
        raise ValueError(
            f"memory forwarding must contain exactly one {CREATE_HELPER} row; found {len(matches)}"
        )
    row = matches[0]
    if row.get("forwarding_confirmed") is not True:
        raise ValueError(f"{CREATE_HELPER}: memory forwarding is not confirmed")
    return row


def _forwarding_sites(wrapper: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    rows = wrapper.get("call_sites")
    if not isinstance(rows, list):
        raise ValueError(f"{CREATE_HELPER}: forwarding call_sites must be a list")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{CREATE_HELPER}: invalid forwarding call site")
        instruction = _norm(row.get("instruction"))
        target = _norm(row.get("target"))
        kind = row.get("transfer_kind")
        if instruction is None or target is None or kind not in {"call", "tail-call"}:
            raise ValueError(f"{CREATE_HELPER}: forwarding site identity/transfer kind missing")
        key = instruction, target
        if key in result:
            raise ValueError(f"{CREATE_HELPER}: duplicate forwarding site {key}")
        result[key] = row
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
    missing = sorted(EXPECTED_BACKENDS - set(result))
    if missing:
        raise ValueError("memory backend evidence missing create backend(s): " + ", ".join(missing))
    return result


def _instruction_index(row: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    instructions = row.get("instructions")
    if not isinstance(instructions, list) or not instructions:
        raise ValueError(f"{CREATE_HELPER}: instructions missing")
    index: dict[str, int] = {}
    for position, instruction in enumerate(instructions):
        if not isinstance(instruction, dict):
            raise ValueError(f"{CREATE_HELPER}: invalid instruction row")
        address = _norm(instruction.get("address"))
        if address is None:
            raise ValueError(f"{CREATE_HELPER}: invalid instruction address")
        if address in index:
            raise ValueError(f"{CREATE_HELPER}: duplicate instruction {address}")
        index[address] = position
    return instructions, index


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


def _eax_register_name(value: str) -> bool:
    return value.strip().upper() in {"EAX", "AX", "AL", "AH"}


@dataclass(frozen=True)
class EaxOrigin:
    kind: str
    target: str | None = None
    instruction: str | None = None
    reason: str | None = None

    def payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "target": self.target,
            "instruction": self.instruction,
            "reason": self.reason,
        }


UNKNOWN = EaxOrigin("unknown")
ENTRY = EaxOrigin("function-entry-eax")


def _writes_eax(mnemonic: str, operands: list[str]) -> bool:
    mnemonic = mnemonic.upper()
    if mnemonic in {"CDQ", "CWD", "CPUID", "RDTSC", "RDTSCP"}:
        return True
    if mnemonic in {"MUL", "DIV", "IDIV"}:
        return True
    if mnemonic == "IMUL" and len(operands) == 1:
        return True
    if not operands:
        return False
    return _eax_register_name(operands[0])


def _transfer_origin(
    instruction: dict[str, Any],
    origin: EaxOrigin,
    forwarding_sites: dict[tuple[str, str], dict[str, Any]],
) -> EaxOrigin:
    address = _norm(instruction.get("address"))
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = [str(value) for value in (instruction.get("operands") or [])]
    opcodes = _pcode_opcodes(instruction)

    if mnemonic == "CALL":
        target = _direct_target(instruction)
        if "CALL" not in opcodes or target is None:
            return EaxOrigin("ambiguous-call", instruction=address, reason="CALL lacks exact p-code/direct target")
        key = (address or "", target)
        if target in EXPECTED_BACKENDS and key in forwarding_sites:
            site = forwarding_sites[key]
            if site.get("transfer_kind") != "call":
                return EaxOrigin("ambiguous-call", target=target, instruction=address, reason="forwarding/raw transfer kind drift")
            return EaxOrigin("backend-call-result-eax", target=target, instruction=address)
        return EaxOrigin("other-call-result-eax", target=target, instruction=address)

    if mnemonic == "MOV" and operands and _eax_register_name(operands[0]):
        if len(operands) >= 2 and operands[1].strip().upper() == "EAX":
            return origin
        return EaxOrigin("eax-overwritten", instruction=address, reason=instruction.get("text"))

    if mnemonic in {"MOVZX", "MOVSX", "LEA", "POP", "XOR", "ADD", "ADC", "SUB", "SBB", "AND", "OR", "INC", "DEC", "NEG", "NOT", "SHL", "SHR", "SAR", "ROL", "ROR", "BSWAP"} and _writes_eax(mnemonic, operands):
        return EaxOrigin("eax-overwritten", instruction=address, reason=instruction.get("text"))

    if _writes_eax(mnemonic, operands):
        return EaxOrigin("eax-overwritten-unsupported", instruction=address, reason=instruction.get("text"))
    return origin


def _internal_successors(
    instruction: dict[str, Any],
    known: set[str],
) -> list[str]:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    flows = [value for value in _flows(instruction) if value in known]
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


def _analyze_exits(
    row: dict[str, Any],
    forwarding_sites: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    instructions, _ = _instruction_index(row)
    by_address = {_norm(item.get("address")): item for item in instructions}
    known = {address for address in by_address if address is not None}
    ordered = sorted(known, key=lambda value: int(value, 16))
    if not ordered:
        raise ValueError(f"{CREATE_HELPER}: no valid instructions")

    queue: deque[tuple[str, EaxOrigin]] = deque([(ordered[0], ENTRY)])
    seen: set[tuple[str, EaxOrigin]] = set()
    ret_origins: dict[str, set[EaxOrigin]] = defaultdict(set)
    tail_exits: dict[str, set[tuple[str, str]]] = defaultdict(set)
    blockers: list[dict[str, Any]] = []
    iterations = 0
    max_iterations = max(256, len(instructions) * 64)

    while queue:
        iterations += 1
        if iterations > max_iterations:
            raise ValueError(f"{CREATE_HELPER}: control-flow analysis iteration limit reached")
        address, origin = queue.popleft()
        state_key = address, origin
        if state_key in seen:
            continue
        seen.add(state_key)
        instruction = by_address[address]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        opcodes = _pcode_opcodes(instruction)

        if mnemonic.startswith("RET"):
            if "RETURN" not in opcodes:
                blockers.append({
                    "id": "ret-without-return-pcode",
                    "instruction": address,
                    "evidence_state": "ambiguous",
                })
            ret_origins[address].add(origin)
            continue

        if mnemonic == "JMP":
            target = _direct_target(instruction)
            internal = target in known if target else False
            if internal:
                if "BRANCH" not in opcodes and "BRANCHIND" not in opcodes:
                    blockers.append({
                        "id": "internal-jmp-without-branch-pcode",
                        "instruction": address,
                        "evidence_state": "ambiguous",
                    })
                queue.append((target, origin))
                continue
            if target in EXPECTED_BACKENDS:
                key = (address, target)
                site = forwarding_sites.get(key)
                if site is None or site.get("transfer_kind") != "tail-call":
                    blockers.append({
                        "id": "tail-backend-forwarding-site-drift",
                        "instruction": address,
                        "target": target,
                        "evidence_state": "ambiguous",
                    })
                    tail_exits[address].add((target, "ambiguous"))
                elif "BRANCH" not in opcodes and "BRANCHIND" not in opcodes:
                    blockers.append({
                        "id": "tail-jmp-without-branch-pcode",
                        "instruction": address,
                        "target": target,
                        "evidence_state": "ambiguous",
                    })
                    tail_exits[address].add((target, "ambiguous"))
                else:
                    tail_exits[address].add((target, "verified"))
                continue
            blockers.append({
                "id": "external-tail-target-not-create-backend",
                "instruction": address,
                "target": target,
                "evidence_state": "unknown",
            })
            tail_exits[address].add((target or "unknown", "unknown"))
            continue

        next_origin = _transfer_origin(instruction, origin, forwarding_sites)
        successors = _internal_successors(instruction, known)
        if not successors:
            blockers.append({
                "id": "reachable-nonterminal-without-successor",
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "evidence_state": "unknown",
            })
            continue
        for successor in successors:
            queue.append((successor, next_origin))

    exits: list[dict[str, Any]] = []
    for address, origins in sorted(ret_origins.items()):
        origin_rows = [item.payload() for item in sorted(origins, key=lambda item: (item.kind, item.target or "", item.instruction or ""))]
        unique_backend = {
            item.target for item in origins
            if item.kind == "backend-call-result-eax" and item.target in EXPECTED_BACKENDS
        }
        verified = len(origins) == 1 and len(unique_backend) == 1
        exits.append({
            "kind": "ret",
            "instruction": address,
            "eax_origins": origin_rows,
            "verified_backend_eax_origin": verified,
            "backend_target": next(iter(unique_backend)) if verified else None,
            "machine_exit_provenance_state": "verified" if verified else "ambiguous",
            "backend_result_semantics_proven": False,
        })
        if not verified:
            blockers.append({
                "id": "ret-eax-origin-not-uniquely-create-backend",
                "instruction": address,
                "origins": origin_rows,
                "evidence_state": "ambiguous",
            })

    for address, targets in sorted(tail_exits.items()):
        rows = [
            {"target": target, "state": state}
            for target, state in sorted(targets)
        ]
        verified = len(rows) == 1 and rows[0]["state"] == "verified"
        exits.append({
            "kind": "tail-call",
            "instruction": address,
            "tail_targets": rows,
            "backend_target": rows[0]["target"] if verified else None,
            "machine_exit_provenance_state": "verified" if verified else "ambiguous",
            "backend_result_semantics_proven": False,
        })

    exits.sort(key=lambda row: int(row["instruction"], 16))
    if not exits:
        raise ValueError(f"{CREATE_HELPER}: no reachable RET or external backend tail exit")
    return exits, blockers


def analyze_vehicle_create_helper_return_provenance(
    lifetime_memory_bridge_path: Path,
    memory_forwarding_path: Path,
    memory_backend_evidence_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    bridge = _load(lifetime_memory_bridge_path, BRIDGE_FORMAT)
    forwarding = _load(memory_forwarding_path, FORWARDING_FORMAT)
    backend = _load(memory_backend_evidence_path, BACKEND_FORMAT)
    instruction_rows = _load_instruction_rows(instruction_export_path)

    bridge_rows = _bridge_rows(bridge)
    wrapper = _forwarding_wrapper(forwarding)
    forwarding_sites = _forwarding_sites(wrapper)
    roles = _backend_roles(backend)
    helper_row = instruction_rows.get(CREATE_HELPER)
    if helper_row is None:
        raise ValueError(f"instruction export missing {CREATE_HELPER}")

    observed_backend_targets = {
        _norm(site.get("target")) for site in wrapper.get("call_sites") or []
    }
    if observed_backend_targets != EXPECTED_BACKENDS:
        raise ValueError(
            f"{CREATE_HELPER}: expected backend set {sorted(EXPECTED_BACKENDS)}, found {sorted(value for value in observed_backend_targets if value)}"
        )

    exits, blockers = _analyze_exits(helper_row, forwarding_sites)
    verified_exit_count = sum(
        row["machine_exit_provenance_state"] == "verified" for row in exits
    )
    all_verified = verified_exit_count == len(exits)
    targets = {row.get("backend_target") for row in exits if row.get("backend_target")}

    allocation_diag = backend.get("allocation_backend_diagnostic_proven") is True
    allocation_path_present = ALLOCATION_BACKEND in targets
    fallback_path_present = FALLBACK_BACKEND in targets
    if not allocation_path_present:
        blockers.append({
            "id": "allocation-diagnostic-backend-not-represented-in-helper-exits",
            "target": ALLOCATION_BACKEND,
            "evidence_state": "unknown",
        })
    if not fallback_path_present:
        blockers.append({
            "id": "create-fallback-backend-not-represented-in-helper-exits",
            "target": FALLBACK_BACKEND,
            "evidence_state": "unknown",
        })

    bridge_outputs = []
    for source in bridge_rows:
        machine_to_initializer = source.get("machine_helper_result_to_initializer_receiver_state")
        bridge_outputs.append({
            "descriptor": source.get("descriptor"),
            "class_name": source.get("class_name"),
            "vehicle_pointer_function": source.get("vehicle_pointer_function"),
            "vehicle_pointer_source_node": source.get("vehicle_pointer_source_node"),
            "stored_table_address": source.get("stored_table_address"),
            "factory_function": source.get("factory_function"),
            "initializer_candidate": source.get("initializer_candidate"),
            "preinitializer_helper": CREATE_HELPER,
            "allocation_request_value": source.get("initializer_backing_allocation_request_value"),
            "allocation_request_state": source.get("initializer_backing_allocation_request_state"),
            "machine_helper_result_to_initializer_receiver_state": machine_to_initializer,
            "helper_machine_exit_provenance_state": "verified" if all_verified else "ambiguous",
            "helper_exit_backend_targets": sorted(targets),
            "helper_return_value_semantics_state": "inferred" if all_verified and machine_to_initializer in {"verified", "inferred", "proven"} else "unknown",
            "helper_return_is_allocated_pointer_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
            "object_size_proven": False,
            "constructor_semantics_proven": False,
            "owner_identity_proven": False,
        })

    blockers.append({
        "id": "backend-return-allocated-pointer-semantics-open",
        "helper": CREATE_HELPER,
        "backend_targets": sorted(EXPECTED_BACKENDS),
        "evidence_state": "unknown",
        "required_evidence": (
            "prove that the value returned by every reachable create backend is the allocated pointer, "
            "without inferring this from allocation diagnostics or helper naming alone"
        ),
    })

    return {
        "format": FORMAT,
        "vehicle_lifetime_memory_bridge": str(lifetime_memory_bridge_path),
        "memory_wrapper_forwarding": str(memory_forwarding_path),
        "memory_backend_evidence": str(memory_backend_evidence_path),
        "instruction_export": str(instruction_export_path),
        "helper": CREATE_HELPER,
        "helper_calling_convention": (helper_row.get("function") or {}).get("calling_convention"),
        "exit_count": len(exits),
        "verified_backend_exit_count": verified_exit_count,
        "all_reachable_helper_exits_backend_sourced": all_verified,
        "exits": exits,
        "backend_roles": [
            {
                "address": target,
                "role": roles[target].get("role"),
                "calling_convention": roles[target].get("calling_convention"),
                "allocation_diagnostic_anchor": target == ALLOCATION_BACKEND and allocation_diag,
                "return_value_semantics_proven": False,
            }
            for target in sorted(EXPECTED_BACKENDS)
        ],
        "allocation_diagnostic_backend_exit_present": allocation_path_present,
        "create_fallback_backend_exit_present": fallback_path_present,
        "allocation_backend_diagnostic_proven": allocation_diag,
        "vehicle_create_bridges": bridge_outputs,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_instruction_export_addresses": sorted(EXPECTED_BACKENDS),
        "scope": {
            "all_helper_exits_analyzed": True,
            "structured_pcode_call_return_branch_used": True,
            "forwarding_site_crosscheck_required": True,
            "backend_role_crosscheck_required": True,
            "backend_call_eax_survival_to_ret_can_be_machine_verified": True,
            "backend_tail_transfer_can_be_machine_verified": True,
            "backend_return_register_semantics_proven": False,
            "allocation_diagnostic_proves_returned_pointer": False,
            "create_fallback_label_proves_returned_pointer": False,
            "helper_return_is_allocated_pointer_proven": False,
            "object_size_proven": False,
            "operator_new_identity_proven": False,
            "constructor_semantics_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
            "owner_identity_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vehicle_lifetime_memory_bridge", type=Path)
    parser.add_argument("memory_wrapper_forwarding", type=Path)
    parser.add_argument("memory_backend_evidence", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--require-all-exits-backend-sourced", action="store_true")
    args = parser.parse_args()

    report = analyze_vehicle_create_helper_return_provenance(
        args.vehicle_lifetime_memory_bridge,
        args.memory_wrapper_forwarding,
        args.memory_backend_evidence,
        args.instruction_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["next_instruction_export_addresses"]),
            encoding="utf-8",
        )
    print(f"format: {report['format']}")
    print(f"helper: {report['helper']}")
    print(f"exits: {report['exit_count']}")
    print(f"verified backend exits: {report['verified_backend_exit_count']}")
    print(f"all exits backend sourced: {report['all_reachable_helper_exits_backend_sourced']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    if args.require_all_exits_backend_sourced and not report["all_reachable_helper_exits_backend_sourced"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

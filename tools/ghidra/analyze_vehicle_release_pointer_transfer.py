#!/usr/bin/env python3
"""Join deleting-wrapper release arguments to the proven retail released-pointer ABI role.

This stage consumes SHIFT.VehicleLifetimeCallsiteTransfer/1 and the canonical
SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1.  It supports one deliberately narrow
machine shape for the semantic Stack[0x4] released-pointer parameter: a full-GPR
PUSH whose value can be traced back to deleting-wrapper entry ECX.  Standard
32-bit x86 nonvolatile-register preservation may be crossed only for exact direct
calls whose target calling convention is present in the same instruction export.

The result proves parameter/value transfer, not operator-delete identity,
destructor semantics, ownership, or same-runtime-object identity.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleReleasePointerTransfer/1"
LIFETIME_FORMAT = "SHIFT.VehicleLifetimeCallsiteTransfer/1"
MANIFEST_FORMAT = "SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"

STATE_STRENGTH = {"unknown": 0, "ambiguous": 1, "inferred": 2, "verified": 3, "proven": 4}
STATES = set(STATE_STRENGTH)
NONVOLATILE_GPRS = {"EBX", "ESI", "EDI", "EBP"}
STANDARD_X86_CC = {"__cdecl", "__stdcall", "__thiscall", "__fastcall"}
SUPPORTED_RELEASE_ENTRY_STORAGE = "Stack[0x4]:4"


def _load_helper():
    path = Path(__file__).with_name("analyze_vehicle_lifetime_callsite_transfer.py")
    spec = importlib.util.spec_from_file_location("vehicle_lifetime_callsite_helper_release", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load helper: {path}")
    spec.loader.exec_module(module)
    return module


def _load(path: Path, expected: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    if payload.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}, found {payload.get('format')}")
    return payload


def _state(value: Any, label: str) -> str:
    if value not in STATES:
        raise ValueError(f"{label}: invalid evidence state {value!r}")
    return str(value)


def _weakest(*values: str) -> str:
    checked = [_state(value, "state merge") for value in values]
    return min(checked, key=lambda value: STATE_STRENGTH[value]) if checked else "unknown"


def _normalize_address(value: Any) -> str:
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        token = value.strip()
        if token.upper().startswith("FUN_"):
            number = int(token[4:], 16)
        else:
            number = int(token, 0)
    else:
        raise ValueError(f"invalid address value {value!r}")
    if number < 0 or number > 0xFFFFFFFF:
        raise ValueError(f"address out of 32-bit range: {value!r}")
    return f"0x{number:08x}"


def _manifest_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = manifest.get("wrappers")
    if not isinstance(rows, list):
        raise ValueError("memory wrapper manifest: wrappers must be a list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("address") is None:
            raise ValueError("memory wrapper manifest: wrapper address missing")
        address = _normalize_address(row["address"])
        if address in result:
            raise ValueError(f"memory wrapper manifest: duplicate wrapper {address}")
        result[address] = row
    return result


def _released_pointer_parameter(wrapper: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    if wrapper.get("forwarding_confirmed") is not True:
        return None, "wrapper-forwarding-unconfirmed"
    params = wrapper.get("parameters")
    if not isinstance(params, list):
        raise ValueError("memory wrapper manifest: parameters must be a list")
    matches = [
        row for row in params
        if isinstance(row, dict)
        and row.get("semantic_role") == "released-pointer"
        and row.get("semantic_role_proven") is True
    ]
    if len(matches) != 1:
        return None, "released-pointer-parameter-not-unique"
    parameter = matches[0]
    if parameter.get("entry_storage") != SUPPORTED_RELEASE_ENTRY_STORAGE:
        return parameter, "released-pointer-storage-shape-unsupported"
    return parameter, "proven-released-pointer-stack-parameter"


def _direct_call_indices(helper, row: dict[str, Any], target: str) -> list[int]:
    return helper._direct_call_indices(row, target)


def _instruction_target(helper, instruction: dict[str, Any]) -> str | None:
    _, _, _, opcodes = helper._parts(instruction, "release-trace")
    if "CALL" not in opcodes:
        return None
    flows = instruction.get("flows")
    if not isinstance(flows, list):
        raise ValueError(f"{instruction.get('address')}: flows must be a list")
    targets = {
        _normalize_address(value)
        for value in flows
        if isinstance(value, str)
    }
    if len(targets) != 1:
        return None
    return next(iter(targets))


def _trace_register_to_wrapper_entry(
    helper,
    rows: dict[str, dict[str, Any]],
    row: dict[str, Any],
    before_index: int,
    register: str,
    *,
    depth: int = 0,
    visited: set[tuple[int, str]] | None = None,
    crossed_calls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if depth > 8:
        return {"evidence_state": "ambiguous", "status": "copy-hop-limit", "source": None, "chain": []}
    visited = set() if visited is None else set(visited)
    crossed_calls = [] if crossed_calls is None else list(crossed_calls)
    key = (before_index, register)
    if key in visited:
        return {"evidence_state": "ambiguous", "status": "copy-cycle", "source": None, "chain": [], "crossed_calls": crossed_calls}
    visited.add(key)
    function = _normalize_address(row["function"]["address"])
    instructions = row["instructions"]

    for index in range(before_index - 1, -1, -1):
        instruction = instructions[index]
        mnemonic, operands, pcode, opcodes = helper._parts(instruction, function)
        address = _normalize_address(instruction["address"])
        if "CALLIND" in opcodes:
            return {
                "evidence_state": "ambiguous",
                "status": "indirect-call-barrier",
                "source": None,
                "chain": [],
                "crossed_calls": crossed_calls,
                "barrier": {"instruction": address, "instruction_text": instruction.get("text")},
            }
        if "CALL" in opcodes:
            target = _instruction_target(helper, instruction)
            callee = rows.get(target) if target is not None else None
            callee_cc = (callee or {}).get("function", {}).get("calling_convention")
            if register not in NONVOLATILE_GPRS or callee is None or callee_cc not in STANDARD_X86_CC:
                return {
                    "evidence_state": "ambiguous",
                    "status": "call-clobber-boundary",
                    "source": None,
                    "chain": [],
                    "crossed_calls": crossed_calls,
                    "barrier": {
                        "instruction": address,
                        "target": target,
                        "tracked_register": register,
                        "callee_calling_convention": callee_cc,
                    },
                }
            crossed_calls.append(
                {
                    "instruction": address,
                    "target": target,
                    "tracked_nonvolatile_register": register,
                    "callee_calling_convention": callee_cc,
                    "preservation_state": "inferred",
                    "note": "uses standard 32-bit x86 nonvolatile-register convention",
                }
            )
            continue

        stop = helper._control_barrier(mnemonic, opcodes)
        if stop is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "control-flow-barrier",
                "source": None,
                "chain": [],
                "crossed_calls": crossed_calls,
                "barrier": {"instruction": address, "reason": stop, "instruction_text": instruction.get("text")},
            }
        implicit = helper._implicit_clobber(mnemonic, operands, register)
        if implicit is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "implicit-register-clobber",
                "source": None,
                "chain": [],
                "crossed_calls": crossed_calls,
                "clobber": {"instruction": address, "reason": implicit, "instruction_text": instruction.get("text")},
            }
        destination = helper._canonical_register(operands[0]) if operands else None
        if destination != register:
            continue
        if mnemonic in helper._NO_WRITE:
            continue
        if helper._full_register(operands[0]) != register:
            return {
                "evidence_state": "ambiguous",
                "status": "partial-register-write",
                "source": None,
                "chain": [],
                "crossed_calls": crossed_calls,
                "clobber": {"instruction": address, "instruction_text": instruction.get("text")},
            }
        if mnemonic != "MOV" or len(operands) < 2:
            return {
                "evidence_state": "ambiguous",
                "status": "unsupported-register-definition",
                "source": None,
                "chain": [],
                "crossed_calls": crossed_calls,
                "clobber": {"instruction": address, "mnemonic": mnemonic, "instruction_text": instruction.get("text")},
            }
        source_register = helper._full_register(operands[1])
        step = {
            "instruction": address,
            "instruction_text": instruction.get("text"),
            "destination_register": register,
            "source_operand": operands[1],
            "pcode": pcode,
        }
        if source_register is None:
            return {
                "evidence_state": "unknown",
                "status": "non-register-source",
                "source": {"kind": "non-register", "operand": operands[1]},
                "chain": [step],
                "crossed_calls": crossed_calls,
            }
        upstream = _trace_register_to_wrapper_entry(
            helper,
            rows,
            row,
            index,
            source_register,
            depth=depth + 1,
            visited=visited,
            crossed_calls=crossed_calls,
        )
        return {
            "evidence_state": upstream["evidence_state"],
            "status": "register-copy-chain",
            "source": upstream.get("source"),
            "chain": [step] + list(upstream.get("chain") or []),
            "crossed_calls": upstream.get("crossed_calls") or crossed_calls,
            "upstream_status": upstream.get("status"),
            "upstream_barrier": upstream.get("barrier"),
            "upstream_clobber": upstream.get("clobber"),
        }

    return {
        "evidence_state": "inferred" if crossed_calls else "verified",
        "status": "wrapper-entry-register",
        "source": {"kind": "function-entry-register", "register": register},
        "chain": [],
        "crossed_calls": crossed_calls,
        "abi_preservation_used": bool(crossed_calls),
    }


def _find_stack_argument_push(
    helper,
    rows: dict[str, dict[str, Any]],
    wrapper_row: dict[str, Any],
    release_index: int,
) -> dict[str, Any]:
    function = _normalize_address(wrapper_row["function"]["address"])
    instructions = wrapper_row["instructions"]
    for index in range(release_index - 1, -1, -1):
        instruction = instructions[index]
        mnemonic, operands, pcode, opcodes = helper._parts(instruction, function)
        address = _normalize_address(instruction["address"])
        if mnemonic == "PUSH":
            if len(operands) != 1:
                return {"evidence_state": "ambiguous", "status": "push-operand-count-unsupported", "instruction": address}
            register = helper._full_register(operands[0])
            if register is None:
                return {
                    "evidence_state": "unknown",
                    "status": "released-pointer-stack-argument-not-full-gpr-push",
                    "instruction": address,
                    "operand": operands[0],
                }
            origin = _trace_register_to_wrapper_entry(helper, rows, wrapper_row, index, register)
            return {
                "evidence_state": _state(origin.get("evidence_state", "unknown"), "release argument origin"),
                "status": "released-pointer-stack-argument-push",
                "push_instruction": address,
                "push_operand": operands[0],
                "push_register": register,
                "callee_entry_storage": SUPPORTED_RELEASE_ENTRY_STORAGE,
                "stack_mapping_state": "verified",
                "origin": origin,
                "note": "PUSH reg followed by CALL maps caller stack-top value to callee Stack[0x4] after return-address push",
            }
        if "CALL" in opcodes or "CALLIND" in opcodes:
            return {
                "evidence_state": "ambiguous",
                "status": "other-call-before-release-stack-argument",
                "barrier": {"instruction": address, "instruction_text": instruction.get("text")},
            }
        stop = helper._control_barrier(mnemonic, opcodes)
        if stop is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "control-flow-before-release-stack-argument",
                "barrier": {"instruction": address, "reason": stop, "instruction_text": instruction.get("text")},
            }
        if helper._implicit_clobber(mnemonic, operands, "ESP") is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "stack-pointer-modified-before-release-call",
                "barrier": {"instruction": address, "instruction_text": instruction.get("text")},
            }
        destination = helper._canonical_register(operands[0]) if operands else None
        if destination == "ESP" and mnemonic not in helper._NO_WRITE:
            return {
                "evidence_state": "ambiguous",
                "status": "explicit-stack-pointer-write-before-release-call",
                "barrier": {"instruction": address, "instruction_text": instruction.get("text")},
            }
    return {"evidence_state": "unknown", "status": "no-supported-release-stack-argument-push"}


def _teardown_entry_value_verified(delete_row: dict[str, Any]) -> bool:
    if delete_row.get("machine_wrapper_entry_to_teardown_receiver_state") != "verified":
        return False
    trace = delete_row.get("machine_wrapper_entry_to_teardown_receiver")
    if not isinstance(trace, dict):
        return False
    source = trace.get("source")
    return (
        isinstance(source, dict)
        and source.get("kind") == "function-entry-register"
        and source.get("register") == "ECX"
    )


def analyze_vehicle_release_pointer_transfer(
    lifetime_transfer_path: Path,
    memory_manifest_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    helper = _load_helper()
    lifetime = _load(lifetime_transfer_path, LIFETIME_FORMAT)
    manifest = _load(memory_manifest_path, MANIFEST_FORMAT)
    rows = helper._load_instructions(instruction_export_path)
    wrappers = _manifest_index(manifest)

    delete_rows = lifetime.get("delete_transfers")
    if not isinstance(delete_rows, list):
        raise ValueError("lifetime callsite transfer: delete_transfers must be a list")

    results: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for delete_row in delete_rows:
        if not isinstance(delete_row, dict):
            raise ValueError("lifetime callsite transfer: invalid delete row")
        descriptor = delete_row.get("descriptor")
        wrapper = delete_row.get("deleting_wrapper_function")
        release = delete_row.get("release_helper")
        if not isinstance(descriptor, int) or not isinstance(wrapper, str) or not isinstance(release, str):
            raise ValueError("lifetime callsite transfer: delete identity missing")
        wrapper = _normalize_address(wrapper)
        release = _normalize_address(release)
        if wrapper not in rows:
            raise ValueError(f"instruction export missing deleting wrapper {wrapper}")

        manifest_row = wrappers.get(release)
        if manifest_row is None:
            parameter = None
            parameter_status = "release-helper-absent-from-memory-wrapper-manifest"
            parameter_state = "unknown"
        else:
            parameter, parameter_status = _released_pointer_parameter(manifest_row)
            parameter_state = "proven" if parameter_status == "proven-released-pointer-stack-parameter" else "unknown"

        wrapper_row = rows[wrapper]
        release_calls = _direct_call_indices(helper, wrapper_row, release)
        if len(release_calls) != 1:
            argument = {
                "evidence_state": "ambiguous",
                "status": "release-callsite-not-unique",
                "release_call_count": len(release_calls),
            }
        elif parameter_status != "proven-released-pointer-stack-parameter":
            argument = {
                "evidence_state": "unknown",
                "status": parameter_status,
            }
        else:
            argument = _find_stack_argument_push(helper, rows, wrapper_row, release_calls[0])

        argument_state = _state(argument.get("evidence_state", "unknown"), "release argument")
        source = ((argument.get("origin") or {}).get("source") if isinstance(argument, dict) else None)
        release_from_entry = (
            isinstance(source, dict)
            and source.get("kind") == "function-entry-register"
            and source.get("register") == "ECX"
        )
        release_entry_state = argument_state if release_from_entry else "unknown"
        teardown_from_entry = _teardown_entry_value_verified(delete_row)
        same_value_state = (
            release_entry_state
            if teardown_from_entry and release_from_entry
            else "unknown"
        )
        wrapper_cc = wrapper_row["function"].get("calling_convention")
        wrapper_receiver_role_state = "inferred" if wrapper_cc == "__thiscall" else "unknown"
        overall = _weakest(parameter_state, same_value_state, wrapper_receiver_role_state)

        result = {
            "descriptor": descriptor,
            "class_name": delete_row.get("class_name"),
            "deleting_wrapper_function": wrapper,
            "release_helper": release,
            "memory_wrapper_manifest_status": manifest_row.get("status") if manifest_row else None,
            "released_pointer_parameter": parameter,
            "released_pointer_parameter_status": parameter_status,
            "released_pointer_parameter_semantic_state": parameter_state,
            "release_call_count": len(release_calls),
            "release_stack_argument": argument,
            "release_stack_argument_machine_state": argument_state,
            "release_argument_originates_at_wrapper_entry_ecx": release_from_entry,
            "wrapper_entry_to_release_parameter_state": release_entry_state,
            "wrapper_entry_to_teardown_receiver_verified": teardown_from_entry,
            "same_wrapper_entry_value_to_teardown_and_release_state": same_value_state,
            "wrapper_receiver_abi_role_state": wrapper_receiver_role_state,
            "release_pointer_lifetime_transfer_state": overall,
            "released_pointer_parameter_semantics_proven": parameter_state == "proven",
            "operator_delete_identity_proven": False,
            "destructor_semantics_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
            "owner_identity_proven": False,
        }
        results.append(result)
        if overall not in {"verified", "proven"}:
            blockers.append(
                {
                    "id": "release-pointer-lifetime-transfer-not-proven",
                    "descriptor": descriptor,
                    "wrapper": wrapper,
                    "release_helper": release,
                    "parameter_status": parameter_status,
                    "argument_status": argument.get("status"),
                    "teardown_from_entry": teardown_from_entry,
                    "wrapper_receiver_abi_role_state": wrapper_receiver_role_state,
                    "evidence_state": overall,
                }
            )

    results.sort(key=lambda row: (row["descriptor"], row["deleting_wrapper_function"], row["release_helper"]))
    return {
        "format": FORMAT,
        "vehicle_lifetime_callsite_transfer": str(lifetime_transfer_path),
        "memory_wrapper_runtime_manifest": str(memory_manifest_path),
        "instruction_export": str(instruction_export_path),
        "transfer_count": len(results),
        "transfers": results,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "scope": {
            "released_pointer_parameter_semantics_can_be_proven": True,
            "stack_0x4_mapping_supports_push_full_gpr_only": True,
            "nonvolatile_register_call_preservation_is_abi_inferred": True,
            "same_wrapper_entry_machine_value_can_feed_teardown_and_release": True,
            "wrapper_entry_ecx_is_object_identity_proof": False,
            "operator_delete_identity_proven": False,
            "destructor_semantics_proven": False,
            "same_runtime_object_across_lifetime_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
            "owner_identity_proven": False,
            "note": (
                "The released-pointer semantic role belongs to one proven helper parameter. "
                "The wrapper-entry ECX role and nonvolatile preservation across teardown calls "
                "remain ABI-backed inference, so whole lifetime object semantics stay gated."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vehicle_lifetime_callsite_transfer", type=Path)
    parser.add_argument("memory_wrapper_runtime_manifest", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_vehicle_release_pointer_transfer(
        args.vehicle_lifetime_callsite_transfer,
        args.memory_wrapper_runtime_manifest,
        args.instruction_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"transfers: {report['transfer_count']}")
    print(f"blockers: {report['blocker_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

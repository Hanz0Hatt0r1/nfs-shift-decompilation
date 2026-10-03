#!/usr/bin/env python3
"""Recover conservative x86 argument forwarding for the retail memory wrappers.

The analyzer consumes the targeted instruction export, the Ghidra function
metadata database, and `SHIFT-MEMORY-WRAPPER-FAMILY/1`. It symbolically models a
small, explicit subset of x86 sufficient for tiny wrapper functions and fails
closed when control flow or state mutation is not understood.

Semantic Ghidra parameter types are retained for audit only. Promotion depends
on physical register/stack storage and concrete instructions.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-MEMORY-WRAPPER-FORWARDING/1"
FAMILY_FORMAT = "SHIFT-MEMORY-WRAPPER-FAMILY/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/1"

_REGISTERS = {
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP",
    "AX", "BX", "CX", "DX", "AL", "AH", "BL", "BH", "CL", "CH", "DL", "DH",
}
_STACK_STORAGE = re.compile(r"^Stack\[0x([0-9a-fA-F]+)\]:(\d+)$")
_MEMORY = re.compile(
    r"^(?:byte|word|dword|qword)\s+ptr\s+\[\s*([A-Za-z]{2,3})\s*(?:([+-])\s*(0x[0-9a-fA-F]+|\d+))?\s*\]$",
    re.IGNORECASE,
)
_IMMEDIATE = re.compile(r"^(?:0x[0-9a-fA-F]+|\d+)$")


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return payload


def _unknown(reason: str) -> dict[str, Any]:
    return {"kind": "unknown", "reason": reason}


def _input(index: int, storage: str) -> dict[str, Any]:
    return {"kind": "input", "index": index, "storage": storage}


def _constant(value: int) -> dict[str, Any]:
    return {"kind": "constant", "value": value, "hex": f"0x{value:x}"}


def _returned(function: str) -> dict[str, Any]:
    return {"kind": "return", "function": function}


def _transform(op: str, source: dict[str, Any], value: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"kind": "transform", "op": op, "source": copy.deepcopy(source)}
    if value is not None:
        result["value"] = value
    return result


def _address(offset: int) -> dict[str, Any]:
    return {"kind": "stack-address", "entry_esp_offset": offset}


def _normalize_storage(storage: str) -> str:
    return storage.replace(" (auto)", "")


def _register_from_storage(storage: str) -> str | None:
    normalized = _normalize_storage(storage)
    if ":" not in normalized or normalized.startswith("Stack["):
        return None
    register = normalized.split(":", 1)[0].upper()
    return register if register in _REGISTERS else None


def _stack_slot(storage: str) -> tuple[int, int] | None:
    match = _STACK_STORAGE.fullmatch(_normalize_storage(storage))
    if not match:
        return None
    return int(match.group(1), 16), int(match.group(2))


def _parse_immediate(value: str) -> int | None:
    token = value.strip()
    if _IMMEDIATE.fullmatch(token) is None:
        return None
    return int(token, 0)


def _collect_input_indices(symbol: dict[str, Any]) -> set[int]:
    kind = symbol.get("kind")
    if kind == "input":
        return {int(symbol["index"])}
    if kind == "transform" and isinstance(symbol.get("source"), dict):
        return _collect_input_indices(symbol["source"])
    return set()


class MachineState:
    def __init__(self, wrapper_function: dict[str, Any]) -> None:
        self.regs: dict[str, dict[str, Any]] = {}
        self.stack: dict[int, dict[str, Any]] = {0: _unknown("return-address")}
        self.esp_offset = 0
        self.pointer_regs: dict[str, int] = {"ESP": 0}
        self.blockers: list[str] = []
        self.nonlinear_control_flow = False
        self.input_count = 0

        for index, parameter in enumerate(wrapper_function.get("parameters") or [], 1):
            if not isinstance(parameter, dict):
                continue
            storage = str(parameter.get("storage") or "")
            symbol = _input(index, storage)
            register = _register_from_storage(storage)
            if register is not None:
                self._write_register(register, symbol)
                self.input_count = max(self.input_count, index)
                continue
            slot = _stack_slot(storage)
            if slot is not None:
                offset, _ = slot
                self.stack[offset] = symbol
                self.input_count = max(self.input_count, index)

    def clone_symbol(self, symbol: dict[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(symbol)

    def _read_register(self, register: str) -> dict[str, Any]:
        reg = register.upper()
        if reg in self.regs:
            return self.clone_symbol(self.regs[reg])
        if reg in {"AL", "AH"} and "EAX" in self.regs:
            return _transform("byte-of-eax", self.regs["EAX"])
        if reg in {"BL", "BH"} and "EBX" in self.regs:
            return _transform("byte-of-ebx", self.regs["EBX"])
        if reg in {"CL", "CH"} and "ECX" in self.regs:
            return _transform("byte-of-ecx", self.regs["ECX"])
        if reg in {"DL", "DH"} and "EDX" in self.regs:
            return _transform("byte-of-edx", self.regs["EDX"])
        return _unknown(f"uninitialized-register:{reg}")

    def _write_register(self, register: str, symbol: dict[str, Any]) -> None:
        reg = register.upper()
        self.regs[reg] = self.clone_symbol(symbol)
        if reg == "EAX":
            self.regs.pop("AL", None); self.regs.pop("AH", None)
        elif reg == "EBX":
            self.regs.pop("BL", None); self.regs.pop("BH", None)
        elif reg == "ECX":
            self.regs.pop("CL", None); self.regs.pop("CH", None)
        elif reg == "EDX":
            self.regs.pop("DL", None); self.regs.pop("DH", None)
        elif reg in {"AL", "AH"}:
            self.regs.pop("EAX", None)
        elif reg in {"BL", "BH"}:
            self.regs.pop("EBX", None)
        elif reg in {"CL", "CH"}:
            self.regs.pop("ECX", None)
        elif reg in {"DL", "DH"}:
            self.regs.pop("EDX", None)

    def _memory_offset(self, operand: str) -> int | None:
        match = _MEMORY.fullmatch(operand.strip())
        if not match:
            return None
        base = match.group(1).upper()
        sign = match.group(2)
        raw_delta = match.group(3)
        if base == "ESP":
            base_offset = self.esp_offset
        else:
            base_offset = self.pointer_regs.get(base)
        if base_offset is None:
            return None
        delta = int(raw_delta, 0) if raw_delta else 0
        if sign == "-":
            delta = -delta
        return base_offset + delta

    def read_operand(self, operand: str) -> dict[str, Any]:
        token = operand.strip()
        upper = token.upper()
        if upper in _REGISTERS:
            return self._read_register(upper)
        immediate = _parse_immediate(token)
        if immediate is not None:
            return _constant(immediate)
        offset = self._memory_offset(token)
        if offset is not None:
            return self.clone_symbol(self.stack.get(offset, _unknown(f"stack-slot:{offset:+#x}")))
        return _unknown(f"unsupported-operand:{token}")

    def write_operand(self, operand: str, symbol: dict[str, Any]) -> bool:
        token = operand.strip()
        upper = token.upper()
        if upper in _REGISTERS:
            self._write_register(upper, symbol)
            self.pointer_regs.pop(upper, None)
            return True
        offset = self._memory_offset(token)
        if offset is not None:
            self.stack[offset] = self.clone_symbol(symbol)
            return True
        return False

    def push(self, symbol: dict[str, Any]) -> None:
        self.esp_offset -= 4
        self.pointer_regs["ESP"] = self.esp_offset
        self.stack[self.esp_offset] = self.clone_symbol(symbol)

    def pop(self) -> dict[str, Any]:
        symbol = self.clone_symbol(self.stack.get(self.esp_offset, _unknown("pop-empty-stack")))
        self.esp_offset += 4
        self.pointer_regs["ESP"] = self.esp_offset
        return symbol

    def adjust_esp(self, delta: int) -> None:
        self.esp_offset += delta
        self.pointer_regs["ESP"] = self.esp_offset

    def bind_target_parameters(self, target: dict[str, Any]) -> list[dict[str, Any]]:
        bindings: list[dict[str, Any]] = []
        for index, parameter in enumerate(target.get("parameters") or [], 1):
            if not isinstance(parameter, dict):
                continue
            storage = str(parameter.get("storage") or "")
            register = _register_from_storage(storage)
            if register is not None:
                source = self._read_register(register)
            else:
                slot = _stack_slot(storage)
                if slot is None:
                    source = _unknown(f"unsupported-target-storage:{storage}")
                else:
                    callee_offset, _ = slot
                    caller_offset = self.esp_offset + callee_offset - 4
                    source = self.clone_symbol(
                        self.stack.get(caller_offset, _unknown(f"caller-stack-slot:{caller_offset:+#x}"))
                    )
            bindings.append(
                {
                    "parameter_index": index,
                    "storage": storage,
                    "reported_type": parameter.get("type"),
                    "source": source,
                    "source_input_indices": sorted(_collect_input_indices(source)),
                }
            )
        return bindings

    def after_call(self, target_address: str, target: dict[str, Any]) -> None:
        # Return value location is architectural; semantic return meaning is not assumed.
        self._write_register("EAX", _returned(target_address))
        self.regs.pop("ECX", None); self.regs.pop("CL", None); self.regs.pop("CH", None)
        self.regs.pop("EDX", None); self.regs.pop("DL", None); self.regs.pop("DH", None)

        convention = target.get("calling_convention")
        if convention in {"__stdcall", "__fastcall", "__thiscall"}:
            cleanup = 0
            for parameter in target.get("parameters") or []:
                if not isinstance(parameter, dict):
                    continue
                slot = _stack_slot(str(parameter.get("storage") or ""))
                if slot is None:
                    continue
                offset, width = slot
                cleanup = max(cleanup, offset - 4 + width)
            if cleanup:
                self.adjust_esp(cleanup)


def _direct_call_target(instruction: dict[str, Any]) -> str | None:
    for reference in instruction.get("references") or []:
        if not isinstance(reference, dict):
            continue
        ref_type = str(reference.get("type") or "").upper()
        target = reference.get("to")
        if "CALL" in ref_type and isinstance(target, str):
            return target
    if str(instruction.get("mnemonic") or "").upper() == "CALL":
        flows = [value for value in instruction.get("flows") or [] if isinstance(value, str)]
        if len(flows) == 1:
            return flows[0]
    return None


def _parse_two_operands(instruction: dict[str, Any]) -> tuple[str, str] | None:
    operands = instruction.get("operands") or []
    if not isinstance(operands, list) or len(operands) != 2:
        return None
    return str(operands[0]), str(operands[1])


def _execute_noncall(state: MachineState, instruction: dict[str, Any]) -> None:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    address = str(instruction.get("address") or "?")
    operands = instruction.get("operands") or []

    if mnemonic in {"NOP", "CMP", "TEST", "RET", "RETN", "INT3"}:
        return
    if mnemonic.startswith("J"):
        state.nonlinear_control_flow = True
        state.blockers.append(f"{address}:control-flow:{mnemonic}")
        return
    if mnemonic == "PUSH" and len(operands) == 1:
        state.push(state.read_operand(str(operands[0])))
        return
    if mnemonic == "POP" and len(operands) == 1:
        if not state.write_operand(str(operands[0]), state.pop()):
            state.blockers.append(f"{address}:unsupported-pop-destination")
        return
    if mnemonic in {"MOV", "MOVZX", "MOVSX"}:
        pair = _parse_two_operands(instruction)
        if pair is None:
            state.blockers.append(f"{address}:invalid-{mnemonic.lower()}-operands")
            return
        destination, source_operand = pair
        if mnemonic == "MOV" and destination.strip().upper() == "EBP" and source_operand.strip().upper() == "ESP":
            state.pointer_regs["EBP"] = state.esp_offset
            state.regs["EBP"] = _address(state.esp_offset)
            return
        source = state.read_operand(source_operand)
        if mnemonic == "MOVZX":
            source = _transform("zero-extend", source)
        elif mnemonic == "MOVSX":
            source = _transform("sign-extend", source)
        if not state.write_operand(destination, source):
            state.blockers.append(f"{address}:unsupported-{mnemonic.lower()}-destination:{destination}")
        return
    if mnemonic == "LEA":
        pair = _parse_two_operands(instruction)
        if pair is None:
            state.blockers.append(f"{address}:invalid-lea-operands")
            return
        destination, source_operand = pair
        offset = state._memory_offset(source_operand)
        if offset is None or destination.strip().upper() not in _REGISTERS:
            state.blockers.append(f"{address}:unsupported-lea")
            return
        register = destination.strip().upper()
        state._write_register(register, _address(offset))
        state.pointer_regs[register] = offset
        return
    if mnemonic in {"ADD", "SUB"}:
        pair = _parse_two_operands(instruction)
        if pair is None:
            state.blockers.append(f"{address}:invalid-{mnemonic.lower()}-operands")
            return
        destination, source_operand = pair
        immediate = _parse_immediate(source_operand)
        if destination.strip().upper() == "ESP" and immediate is not None:
            state.adjust_esp(immediate if mnemonic == "ADD" else -immediate)
            return
        register = destination.strip().upper()
        if register in _REGISTERS and immediate is not None:
            state._write_register(
                register,
                _transform(mnemonic.lower(), state._read_register(register), immediate),
            )
            return
        state.blockers.append(f"{address}:unsupported-{mnemonic.lower()}")
        return
    if mnemonic == "XOR":
        pair = _parse_two_operands(instruction)
        if pair is not None and pair[0].strip().upper() == pair[1].strip().upper():
            register = pair[0].strip().upper()
            if register in _REGISTERS:
                state._write_register(register, _constant(0))
                return
        state.blockers.append(f"{address}:unsupported-xor")
        return
    if mnemonic == "LEAVE":
        ebp_offset = state.pointer_regs.get("EBP")
        if ebp_offset is None:
            state.blockers.append(f"{address}:leave-without-frame")
            return
        state.esp_offset = ebp_offset
        state.pointer_regs["ESP"] = ebp_offset
        state._write_register("EBP", state.pop())
        state.pointer_regs.pop("EBP", None)
        return

    state.blockers.append(f"{address}:unmodeled-instruction:{mnemonic}")


def _functions_index(ghidra_export: Path) -> dict[str, dict[str, Any]]:
    path = ghidra_export / "functions.jsonl"
    if not path.is_file():
        raise FileNotFoundError(path)
    return {
        row["address"]: row
        for row in _read_jsonl(path)
        if isinstance(row.get("address"), str)
    }


def _instruction_index(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
        if row.get("found") is not True:
            continue
        function = row.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("address"), str):
            raise ValueError(f"{path}: invalid function row")
        rows[function["address"]] = row
    return rows


def _analyze_wrapper(
    wrapper: dict[str, Any],
    instruction_row: dict[str, Any] | None,
    functions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    address = wrapper.get("address")
    function = functions.get(address) if isinstance(address, str) else None
    required = set(wrapper.get("required_direct_callees") or [])
    if function is None or instruction_row is None:
        return {
            "address": address,
            "name": wrapper.get("name"),
            "instruction_export_present": instruction_row is not None,
            "function_metadata_present": function is not None,
            "expected_backend_calls": sorted(required),
            "backend_calls": [],
            "blockers": ["missing-function-metadata" if function is None else "missing-instruction-export"],
            "exact_forwarding_candidate": False,
        }

    state = MachineState(function)
    calls: list[dict[str, Any]] = []
    observed_required: set[str] = set()

    for instruction in instruction_row.get("instructions") or []:
        if not isinstance(instruction, dict):
            state.blockers.append("invalid-instruction-row")
            continue
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        if mnemonic == "CALL":
            target_address = _direct_call_target(instruction)
            if target_address is None:
                state.blockers.append(f"{instruction.get('address')}:unresolved-call-target")
                state._write_register("EAX", _unknown("return-from-unresolved-call"))
                continue
            target = functions.get(target_address)
            if target is None:
                state.blockers.append(f"{instruction.get('address')}:missing-target-metadata:{target_address}")
                state._write_register("EAX", _returned(target_address))
                continue
            bindings = state.bind_target_parameters(target)
            unresolved = sum(binding["source"].get("kind") == "unknown" for binding in bindings)
            call = {
                "instruction": instruction.get("address"),
                "target": target_address,
                "target_name": target.get("name"),
                "target_calling_convention": target.get("calling_convention"),
                "target_parameter_bindings": bindings,
                "unresolved_parameter_count": unresolved,
                "binding_complete": unresolved == 0,
                "required_backend_call": target_address in required,
            }
            calls.append(call)
            if target_address in required:
                observed_required.add(target_address)
            state.after_call(target_address, target)
            continue
        _execute_noncall(state, instruction)

    required_calls = [call for call in calls if call["required_backend_call"]]
    all_required_seen = required.issubset(observed_required)
    bindings_complete = bool(required_calls) and all(call["binding_complete"] for call in required_calls)
    exact = bool(
        wrapper.get("wrapper_shape_confirmed") is True
        and all_required_seen
        and bindings_complete
        and not state.nonlinear_control_flow
        and not state.blockers
    )
    forwarded_inputs = sorted(
        {
            index
            for call in required_calls
            for binding in call["target_parameter_bindings"]
            for index in binding["source_input_indices"]
        }
    )
    declared_inputs = list(range(1, state.input_count + 1))

    return {
        "address": address,
        "name": wrapper.get("name"),
        "side": wrapper.get("side"),
        "instruction_export_present": True,
        "function_metadata_present": True,
        "declared_input_count": state.input_count,
        "expected_backend_calls": sorted(required),
        "observed_required_backend_calls": sorted(observed_required),
        "all_expected_backend_calls_seen": all_required_seen,
        "backend_bindings_complete": bindings_complete,
        "forwarded_wrapper_inputs": forwarded_inputs,
        "unforwarded_declared_inputs": [value for value in declared_inputs if value not in forwarded_inputs],
        "backend_calls": calls,
        "nonlinear_control_flow": state.nonlinear_control_flow,
        "blockers": state.blockers,
        "exact_forwarding_candidate": exact,
        "scope": {
            "semantic_parameter_types_used": False,
            "argument_roles_assigned": False,
        },
    }


def analyze_memory_wrapper_forwarding(
    family_path: Path,
    instruction_export: Path,
    ghidra_export: Path,
) -> dict[str, Any]:
    family = _load_json(family_path, FAMILY_FORMAT)
    functions = _functions_index(ghidra_export)
    instructions = _instruction_index(instruction_export)
    wrappers = [
        _analyze_wrapper(wrapper, instructions.get(wrapper.get("address")), functions)
        for wrapper in (family.get("wrappers") or [])
        if isinstance(wrapper, dict)
    ]
    wrappers.sort(key=lambda row: str(row.get("address") or ""))
    exact_count = sum(row.get("exact_forwarding_candidate") is True for row in wrappers)
    return {
        "format": FORMAT,
        "memory_wrapper_family": str(family_path),
        "instruction_export": str(instruction_export),
        "ghidra_export": str(ghidra_export),
        "wrapper_count": len(wrappers),
        "exact_forwarding_wrapper_count": exact_count,
        "all_family_wrappers_exact": bool(wrappers and exact_count == len(wrappers)),
        "wrappers": wrappers,
        "scope": {
            "instruction_bytes_used": True,
            "physical_parameter_storage_used": True,
            "semantic_parameter_types_used": False,
            "argument_forwarding_proven_when_exact": True,
            "argument_roles_proven": False,
            "allocator_abi_proven": False,
            "release_abi_proven": False,
            "operator_new_identity_proven": False,
            "operator_delete_identity_proven": False,
            "note": (
                "Exact rows prove only concrete movement of wrapper inputs/constants "
                "into backend physical parameter slots along the modeled straight-line "
                "instruction path. They do not assign semantic roles such as size, "
                "pool, tag or delete flags."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", type=Path, help="SHIFT-MEMORY-WRAPPER-FAMILY/1 JSON")
    parser.add_argument("instructions", type=Path, help="SHIFT.GhidraFunctionInstructions/1 JSONL")
    parser.add_argument("--ghidra-export", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_memory_wrapper_forwarding(args.family, args.instructions, args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"wrappers: {report['wrapper_count']}")
    print(f"exact forwarding wrappers: {report['exact_forwarding_wrapper_count']}")
    print(f"all family wrappers exact: {report['all_family_wrappers_exact']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

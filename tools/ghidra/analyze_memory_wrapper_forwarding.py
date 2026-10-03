#!/usr/bin/env python3
"""Recover conservative argument forwarding for the retail memory-wrapper cluster.

The input is the targeted instruction JSONL emitted by
ShiftFunctionInstructionExporter.java.  This analyzer deliberately implements a
small x86 data-flow subset and fails closed when an instruction or merge cannot
be represented exactly.  It proves storage/value forwarding into known backend
calls; it does not assign semantic roles such as size, pool, alignment or delete
kind.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-MEMORY-WRAPPER-FORWARDING/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/1"
UNKNOWN = "unresolved"

WRAPPER_SPECS: dict[str, dict[str, Any]] = {
    "0x008868c0": {
        "name": "FUN_008868c0",
        "input_storage": ["Stack[0x4]:4"],
        "required_backends": ["0x006382b0"],
    },
    "0x008868d0": {
        "name": "FUN_008868d0",
        "input_storage": ["Stack[0x4]:4", "Stack[0x8]:4"],
        "required_backends": ["0x00638020", "0x006382b0"],
    },
    "0x00886900": {
        "name": "FUN_00886900",
        "input_storage": ["Stack[0x4]:4", "Stack[0x8]:4", "Stack[0xc]:4"],
        "required_backends": ["0x00638020", "0x006382b0"],
    },
    "0x00886930": {
        "name": "FUN_00886930",
        "input_storage": ["ECX:4", "DL:1", "Stack[0x4]:4"],
        "required_backends": ["0x0064f4c0"],
    },
    "0x00886950": {
        "name": "FUN_00886950",
        "input_storage": ["ECX:4", "DL:1", "Stack[0x4]:4", "Stack[0x8]:4"],
        "required_backends": ["0x0064f260", "0x0064f4c0"],
    },
}

BACKEND_SPECS: dict[str, dict[str, Any]] = {
    "0x006382b0": {
        "name": "FUN_006382b0",
        "calling_convention": "__fastcall",
        "parameter_storage": ["ECX:4", "EDX:4"],
    },
    "0x00638020": {
        "name": "FUN_00638020",
        "calling_convention": "__fastcall",
        "parameter_storage": ["ECX:4", "EDX:4", "Stack[0x4]:4"],
    },
    "0x0064f4c0": {
        "name": "thunk_FUN_0064f3a0",
        "calling_convention": "__fastcall",
        "parameter_storage": ["ECX:4", "DL:1"],
    },
    "0x0064f260": {
        "name": "FUN_0064f260",
        "calling_convention": "__fastcall",
        "parameter_storage": ["ECX:4", "EDX:4"],
    },
}

REGISTER_NAMES = {
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP",
    "AL", "AH", "BL", "BH", "CL", "CH", "DL", "DH",
}
VOLATILE_DWORDS = ("EAX", "ECX", "EDX")
SIZE_PREFIX = re.compile(r"^(?:BYTE|WORD|DWORD|QWORD)\s+PTR\s+", re.IGNORECASE)
STACK_MEMORY = re.compile(
    r"^\[(ESP|EBP)(?:\s*([+-])\s*(0X[0-9A-F]+|[0-9]+))?\]$",
    re.IGNORECASE,
)
STACK_STORAGE = re.compile(r"^Stack\[0x([0-9a-fA-F]+)\]:(\d+)$")


def _norm_address(value: str | None) -> str | None:
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
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _input_expr(storage: str) -> str:
    return f"input:{storage}"


def _const_expr(value: int) -> str:
    return f"constant:0x{value & 0xffffffff:x}"


def _merge_expr(left: str | None, right: str | None) -> str:
    if left == right and left is not None:
        return left
    return UNKNOWN


@dataclass
class State:
    regs: dict[str, str] = field(default_factory=dict)
    stack: dict[int, str] = field(default_factory=dict)
    esp_delta: int | None = 0
    ebp_delta: int | None = None
    uncertain: bool = False
    reasons: set[str] = field(default_factory=set)

    def copy(self) -> "State":
        return State(
            regs=dict(self.regs),
            stack=dict(self.stack),
            esp_delta=self.esp_delta,
            ebp_delta=self.ebp_delta,
            uncertain=self.uncertain,
            reasons=set(self.reasons),
        )

    def signature(self) -> tuple[Any, ...]:
        return (
            tuple(sorted(self.regs.items())),
            tuple(sorted(self.stack.items())),
            self.esp_delta,
            self.ebp_delta,
            self.uncertain,
            tuple(sorted(self.reasons)),
        )


def _merge_state(old: State | None, new: State) -> tuple[State, bool]:
    if old is None:
        return new.copy(), True
    merged = State()
    merged.esp_delta = old.esp_delta if old.esp_delta == new.esp_delta else None
    merged.ebp_delta = old.ebp_delta if old.ebp_delta == new.ebp_delta else None
    merged.uncertain = old.uncertain or new.uncertain
    merged.reasons = set(old.reasons) | set(new.reasons)
    if old.esp_delta != new.esp_delta:
        merged.uncertain = True
        merged.reasons.add("control-flow merge has different ESP deltas")
    if old.ebp_delta != new.ebp_delta and old.ebp_delta is not None and new.ebp_delta is not None:
        merged.uncertain = True
        merged.reasons.add("control-flow merge has different EBP bases")

    for key in set(old.regs) | set(new.regs):
        merged.regs[key] = _merge_expr(old.regs.get(key), new.regs.get(key))
    for key in set(old.stack) | set(new.stack):
        merged.stack[key] = _merge_expr(old.stack.get(key), new.stack.get(key))

    changed = merged.signature() != old.signature()
    return merged, changed


def _initial_state(spec: dict[str, Any]) -> State:
    state = State()
    for storage in spec["input_storage"]:
        if storage.startswith("Stack["):
            match = STACK_STORAGE.match(storage)
            if match:
                state.stack[int(match.group(1), 16)] = _input_expr(storage)
            continue
        register = storage.split(":", 1)[0].upper()
        state.regs[register] = _input_expr(storage)
        if register == "EDX":
            state.regs["DL"] = f"low8({_input_expr(storage)})"
    return state


def _clean_operand(operand: str) -> str:
    value = SIZE_PREFIX.sub("", operand.strip()).strip()
    return re.sub(r"\s+", " ", value).upper()


def _parse_immediate(value: str) -> int | None:
    token = value.strip().upper()
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


def _stack_offset(state: State, operand: str) -> int | None:
    match = STACK_MEMORY.match(_clean_operand(operand))
    if not match:
        return None
    base = match.group(1).upper()
    base_delta = state.esp_delta if base == "ESP" else state.ebp_delta
    if base_delta is None:
        return None
    displacement = 0
    if match.group(3):
        raw = int(match.group(3), 0)
        displacement = -raw if match.group(2) == "-" else raw
    return base_delta + displacement


def _register_value(state: State, register: str) -> str:
    reg = register.upper()
    if reg in state.regs:
        return state.regs[reg]
    if reg == "DL" and "EDX" in state.regs:
        return f"low8({state.regs['EDX']})"
    return UNKNOWN


def _read_operand(state: State, operand: str, *, address_only: bool = False) -> str:
    cleaned = _clean_operand(operand)
    if cleaned in REGISTER_NAMES:
        return _register_value(state, cleaned)
    offset = _stack_offset(state, cleaned)
    if offset is not None:
        if address_only:
            sign = "+" if offset >= 0 else "-"
            return f"address:entry_stack{sign}0x{abs(offset):x}"
        return state.stack.get(offset, UNKNOWN)
    immediate = _parse_immediate(cleaned)
    if immediate is not None:
        return _const_expr(immediate)
    return UNKNOWN


def _set_register(state: State, register: str, value: str) -> None:
    reg = register.upper()
    state.regs[reg] = value
    if reg == "EDX":
        state.regs["DL"] = f"low8({value})" if value != UNKNOWN else UNKNOWN
    elif reg == "DL":
        # A byte write does not prove the upper EDX bits.
        state.regs["EDX"] = UNKNOWN


def _write_operand(state: State, operand: str, value: str) -> bool:
    cleaned = _clean_operand(operand)
    if cleaned in REGISTER_NAMES:
        _set_register(state, cleaned, value)
        return True
    offset = _stack_offset(state, cleaned)
    if offset is not None:
        state.stack[offset] = value
        return True
    return False


def _mark_uncertain(state: State, instruction: dict[str, Any], reason: str) -> None:
    state.uncertain = True
    address = instruction.get("address") or "?"
    mnemonic = instruction.get("mnemonic") or "?"
    state.reasons.add(f"{address} {mnemonic}: {reason}")


def _binary_expr(op: str, left: str, right: str) -> str:
    if left == UNKNOWN or right == UNKNOWN:
        return UNKNOWN
    return f"{op}({left},{right})"


def _call_target(instruction: dict[str, Any]) -> str | None:
    for ref in instruction.get("references") or []:
        if not isinstance(ref, dict):
            continue
        ref_type = str(ref.get("type") or "").upper()
        target = _norm_address(ref.get("to"))
        if target and "CALL" in ref_type:
            return target
    for value in instruction.get("flows") or []:
        target = _norm_address(value)
        if target:
            return target
    return None


def _stack_cleanup_bytes(backend: dict[str, Any]) -> int:
    convention = backend.get("calling_convention")
    if convention not in {"__fastcall", "__stdcall"}:
        return 0
    count = sum(str(storage).startswith("Stack[") for storage in backend["parameter_storage"])
    return count * 4


def _transfer(state: State, instruction: dict[str, Any]) -> State:
    out = state.copy()
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = [str(value) for value in (instruction.get("operands") or [])]

    if mnemonic in {"NOP", "TEST", "CMP"} or mnemonic.startswith("J") or mnemonic.startswith("RET"):
        return out

    if mnemonic == "MOV" and len(operands) == 2:
        value = _read_operand(out, operands[1])
        if not _write_operand(out, operands[0], value):
            _mark_uncertain(out, instruction, "unsupported MOV destination")
        if _clean_operand(operands[0]) == "EBP" and _clean_operand(operands[1]) == "ESP":
            out.ebp_delta = out.esp_delta
        return out

    if mnemonic == "LEA" and len(operands) == 2:
        value = _read_operand(out, operands[1], address_only=True)
        if not _write_operand(out, operands[0], value):
            _mark_uncertain(out, instruction, "unsupported LEA destination")
        return out

    if mnemonic in {"MOVZX", "MOVSX"} and len(operands) == 2:
        value = _read_operand(out, operands[1])
        if value != UNKNOWN:
            value = f"{mnemonic.lower()}({value})"
        if not _write_operand(out, operands[0], value):
            _mark_uncertain(out, instruction, f"unsupported {mnemonic} destination")
        return out

    if mnemonic == "XOR" and len(operands) == 2:
        if _clean_operand(operands[0]) == _clean_operand(operands[1]):
            if not _write_operand(out, operands[0], _const_expr(0)):
                _mark_uncertain(out, instruction, "unsupported XOR zero destination")
            return out

    if mnemonic in {"ADD", "SUB"} and len(operands) == 2 and _clean_operand(operands[0]) == "ESP":
        amount = _parse_immediate(_clean_operand(operands[1]))
        if amount is None or out.esp_delta is None:
            out.esp_delta = None
            _mark_uncertain(out, instruction, "non-constant ESP adjustment")
        else:
            out.esp_delta += amount if mnemonic == "ADD" else -amount
        return out

    if mnemonic in {"ADD", "SUB", "AND", "OR"} and len(operands) == 2:
        left = _read_operand(out, operands[0])
        right = _read_operand(out, operands[1])
        value = _binary_expr(mnemonic.lower(), left, right)
        if not _write_operand(out, operands[0], value):
            _mark_uncertain(out, instruction, f"unsupported {mnemonic} destination")
        return out

    if mnemonic == "PUSH" and len(operands) == 1:
        value = _read_operand(out, operands[0])
        if out.esp_delta is None:
            _mark_uncertain(out, instruction, "PUSH with unresolved ESP")
        else:
            out.esp_delta -= 4
            out.stack[out.esp_delta] = value
        return out

    if mnemonic == "POP" and len(operands) == 1:
        if out.esp_delta is None:
            _mark_uncertain(out, instruction, "POP with unresolved ESP")
        else:
            value = out.stack.get(out.esp_delta, UNKNOWN)
            if not _write_operand(out, operands[0], value):
                _mark_uncertain(out, instruction, "unsupported POP destination")
            out.esp_delta += 4
        return out

    if mnemonic == "LEAVE":
        if out.ebp_delta is None:
            out.esp_delta = None
            _mark_uncertain(out, instruction, "LEAVE without known EBP base")
        else:
            out.esp_delta = out.ebp_delta
            out.regs["EBP"] = out.stack.get(out.esp_delta, UNKNOWN)
            out.esp_delta += 4
            out.ebp_delta = None
        return out

    if mnemonic == "CALL":
        target = _call_target(instruction)
        backend = BACKEND_SPECS.get(target or "")
        _set_register(out, "EAX", f"return:{target or 'unknown-call'}")
        _set_register(out, "ECX", UNKNOWN)
        _set_register(out, "EDX", UNKNOWN)
        if backend is None:
            _mark_uncertain(out, instruction, "call target is not a modeled backend")
        elif out.esp_delta is not None:
            out.esp_delta += _stack_cleanup_bytes(backend)
        return out

    _mark_uncertain(out, instruction, "instruction is outside the modeled x86 subset")
    return out


def _successors(
    instruction: dict[str, Any],
    function_addresses: set[str],
) -> list[str]:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    fallthrough = _norm_address(instruction.get("fallthrough"))
    flows = [
        target
        for target in (_norm_address(value) for value in (instruction.get("flows") or []))
        if target in function_addresses
    ]
    if mnemonic.startswith("RET"):
        return []
    if mnemonic == "JMP":
        return flows
    if mnemonic.startswith("J"):
        result = list(flows)
        if fallthrough in function_addresses and fallthrough not in result:
            result.append(fallthrough)
        return result
    if fallthrough in function_addresses:
        return [fallthrough]
    return []


def _source_kind(value: str) -> str:
    if value == UNKNOWN:
        return "unresolved"
    if value.startswith("input:"):
        return "input"
    if "input:" in value:
        return "derived-input"
    if value.startswith("constant:"):
        return "constant"
    if value.startswith("return:"):
        return "call-return"
    if value.startswith("address:"):
        return "address"
    return "derived"


def _backend_arguments(state: State, backend: dict[str, Any]) -> list[dict[str, Any]]:
    arguments: list[dict[str, Any]] = []
    for storage in backend["parameter_storage"]:
        if storage.startswith("Stack["):
            match = STACK_STORAGE.match(storage)
            if match is None or state.esp_delta is None:
                value = UNKNOWN
            else:
                callee_offset = int(match.group(1), 16)
                caller_offset = state.esp_delta + callee_offset - 4
                value = state.stack.get(caller_offset, UNKNOWN)
        else:
            register = storage.split(":", 1)[0].upper()
            value = _register_value(state, register)
        arguments.append(
            {
                "storage": storage,
                "source": value,
                "source_kind": _source_kind(value),
                "resolved": value != UNKNOWN,
            }
        )
    return arguments


def _analyze_wrapper(row: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    function = row.get("function") or {}
    address = _norm_address(function.get("address"))
    instructions = [item for item in (row.get("instructions") or []) if isinstance(item, dict)]
    by_address = {
        normalized: item
        for item in instructions
        if (normalized := _norm_address(item.get("address"))) is not None
    }
    ordered = sorted(by_address)
    if not ordered:
        return {
            "address": address,
            "name": spec["name"],
            "instruction_count": 0,
            "required_backend_targets": list(spec["required_backends"]),
            "observed_backend_targets": [],
            "call_sites": [],
            "required_backends_present": False,
            "all_call_arguments_resolved": False,
            "forwarding_confirmed": False,
            "uncertainty_reasons": ["function has no instructions"],
        }

    in_states: dict[str, State] = {ordered[0]: _initial_state(spec)}
    queue: deque[str] = deque([ordered[0]])
    iterations = 0
    max_iterations = max(64, len(ordered) * 32)
    while queue:
        iterations += 1
        if iterations > max_iterations:
            state = in_states[queue[0]]
            state.uncertain = True
            state.reasons.add("data-flow iteration limit reached")
            break
        current = queue.popleft()
        instruction = by_address[current]
        out = _transfer(in_states[current], instruction)
        for successor in _successors(instruction, set(by_address)):
            merged, changed = _merge_state(in_states.get(successor), out)
            if changed:
                in_states[successor] = merged
                queue.append(successor)

    call_sites: list[dict[str, Any]] = []
    observed_targets: set[str] = set()
    reasons: set[str] = set()
    for instruction_address in ordered:
        instruction = by_address[instruction_address]
        if str(instruction.get("mnemonic") or "").upper() != "CALL":
            continue
        target = _call_target(instruction)
        if target not in BACKEND_SPECS:
            continue
        state = in_states.get(instruction_address)
        if state is None:
            continue
        backend = BACKEND_SPECS[target]
        arguments = _backend_arguments(state, backend)
        observed_targets.add(target)
        reasons.update(state.reasons)
        call_sites.append(
            {
                "instruction": instruction_address,
                "target": target,
                "target_name": backend["name"],
                "target_calling_convention": backend["calling_convention"],
                "arguments": arguments,
                "arguments_resolved": all(item["resolved"] for item in arguments),
                "incoming_state_uncertain": state.uncertain,
                "uncertainty_reasons": sorted(state.reasons),
            }
        )

    required = set(spec["required_backends"])
    required_present = required.issubset(observed_targets)
    relevant_sites = [site for site in call_sites if site["target"] in required]
    all_resolved = bool(relevant_sites) and all(
        site["arguments_resolved"] and not site["incoming_state_uncertain"]
        for site in relevant_sites
    )
    forwarding_confirmed = bool(required_present and all_resolved)
    if not required_present:
        reasons.add("one or more required backend calls are missing")

    return {
        "address": address,
        "name": spec["name"],
        "calling_convention": function.get("calling_convention"),
        "input_storage": list(spec["input_storage"]),
        "instruction_count": len(instructions),
        "reachable_instruction_count": len(in_states),
        "required_backend_targets": list(spec["required_backends"]),
        "observed_backend_targets": sorted(observed_targets),
        "call_sites": call_sites,
        "required_backends_present": required_present,
        "all_call_arguments_resolved": all_resolved,
        "forwarding_confirmed": forwarding_confirmed,
        "uncertainty_reasons": sorted(reasons),
    }


def analyze_memory_wrapper_forwarding(path: Path) -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = {}
    programs: set[str] = set()
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved requested function {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict):
            raise ValueError(f"{path}: function record missing")
        address = _norm_address(function.get("address"))
        if address is None:
            raise ValueError(f"{path}: invalid function address {function.get('address')!r}")
        rows[address] = row
        if isinstance(row.get("program"), str):
            programs.add(row["program"])

    missing = [address for address in WRAPPER_SPECS if address not in rows]
    if missing:
        raise ValueError("instruction export missing wrappers: " + ", ".join(missing))

    wrappers = [
        _analyze_wrapper(rows[address], spec)
        for address, spec in WRAPPER_SPECS.items()
    ]
    confirmed = sum(wrapper["forwarding_confirmed"] is True for wrapper in wrappers)
    return {
        "format": FORMAT,
        "instruction_export": str(path),
        "programs": sorted(programs),
        "wrapper_count": len(wrappers),
        "confirmed_wrapper_forwarding_count": confirmed,
        "all_wrapper_forwarding_confirmed": confirmed == len(wrappers),
        "wrappers": wrappers,
        "backend_specs": BACKEND_SPECS,
        "scope": {
            "instruction_level_dataflow_used": True,
            "raw_operand_storage_used": True,
            "control_flow_merges_fail_closed": True,
            "unsupported_instructions_fail_closed": True,
            "argument_forwarding_proven": confirmed == len(wrappers),
            "argument_semantic_roles_proven": False,
            "allocator_abi_proven": False,
            "release_abi_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "A confirmed wrapper proves how values from entry storage, constants or "
                "prior call returns reach the physical argument storage of known backend "
                "calls. It does not name those values as byte size, alignment, pool id, "
                "delete kind or ownership state."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_memory_wrapper_forwarding(args.instruction_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"wrappers: {report['wrapper_count']}")
    print(f"confirmed forwarding: {report['confirmed_wrapper_forwarding_count']}")
    print(f"all forwarding confirmed: {report['all_wrapper_forwarding_confirmed']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

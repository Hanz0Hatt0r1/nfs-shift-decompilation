#!/usr/bin/env python3
"""Track entry DL influence through the retail release thunk/backend.

This is a behavior/taint analyzer, not a semantic-role promoter. It records
whether the entry low byte reaches tests/comparisons, conditional branches,
bitwise transforms, and outgoing transfers in 0x0064f4c0 / FUN_0064f3a0.
A positive observation does not by itself prove `delete flag`, destructor kind,
or ownership semantics.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-MEMORY-RELEASE-BYTE-BEHAVIOR/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/1"
THUNK = "0x0064f4c0"
RELEASE_BACKEND = "0x0064f3a0"
TARGETS = (THUNK, RELEASE_BACKEND)

SIZE_PREFIX = re.compile(r"^(?:BYTE|WORD|DWORD|QWORD)\s+PTR\s+", re.IGNORECASE)
REGISTER_NAMES = {
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP",
    "AL", "AH", "BL", "BH", "CL", "CH", "DL", "DH",
}
BITWISE_MNEMONICS = {"AND", "OR", "XOR", "SHL", "SHR", "SAR", "ROL", "ROR"}
BINARY_WRITE_MNEMONICS = BITWISE_MNEMONICS | {"ADD", "SUB", "ADC", "SBB"}


def _norm_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("thunk_fun_"):
        token = token[10:]
    elif token.startswith("fun_"):
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


def _load_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
        if row.get("found") is not True:
            continue
        function = row.get("function")
        if not isinstance(function, dict):
            continue
        address = _norm_address(function.get("address"))
        if address is not None:
            rows[address] = row
    missing = [address for address in TARGETS if address not in rows]
    if missing:
        raise ValueError("instruction export missing release-byte functions: " + ", ".join(missing))
    return rows


def _clean_operand(value: str) -> str:
    return re.sub(r"\s+", " ", SIZE_PREFIX.sub("", value.strip()).strip()).upper()


def _memory_key(operand: str) -> str | None:
    cleaned = _clean_operand(operand)
    return cleaned if "[" in cleaned and "]" in cleaned else None


def _register_tokens(operand: str) -> set[str]:
    cleaned = _clean_operand(operand)
    return {
        reg
        for reg in REGISTER_NAMES
        if re.search(rf"(?<![A-Z0-9_]){re.escape(reg)}(?![A-Z0-9_])", cleaned)
    }


def _transfer_target(instruction: dict[str, Any]) -> str | None:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    if mnemonic not in {"CALL", "JMP"}:
        return None
    for ref in instruction.get("references") or []:
        if isinstance(ref, dict):
            target = _norm_address(ref.get("to"))
            if target is not None:
                return target
    for value in instruction.get("flows") or []:
        target = _norm_address(value)
        if target is not None:
            return target
    operands = instruction.get("operands") or []
    if operands:
        return _norm_address(str(operands[0]))
    return None


@dataclass
class State:
    regs: dict[str, bool] = field(default_factory=dict)
    memory: dict[str, bool] = field(default_factory=dict)
    condition_tainted: bool = False
    uncertain: bool = False
    reasons: set[str] = field(default_factory=set)

    def copy(self) -> "State":
        return State(
            regs=dict(self.regs),
            memory=dict(self.memory),
            condition_tainted=self.condition_tainted,
            uncertain=self.uncertain,
            reasons=set(self.reasons),
        )

    def signature(self) -> tuple[Any, ...]:
        return (
            tuple(sorted(self.regs.items())),
            tuple(sorted(self.memory.items())),
            self.condition_tainted,
            self.uncertain,
            tuple(sorted(self.reasons)),
        )


def _initial_state() -> State:
    state = State()
    for reg in REGISTER_NAMES:
        state.regs[reg] = False
    # EDX contains DL as its low byte on function entry, so a dword read of EDX
    # is also influenced by entry DL until EDX/DL is overwritten.
    state.regs["DL"] = True
    state.regs["EDX"] = True
    return state


def _merge_state(old: State | None, new: State) -> tuple[State, bool]:
    if old is None:
        return new.copy(), True
    merged = State()
    for key in set(old.regs) | set(new.regs):
        merged.regs[key] = bool(old.regs.get(key, False) or new.regs.get(key, False))
    for key in set(old.memory) | set(new.memory):
        merged.memory[key] = bool(old.memory.get(key, False) or new.memory.get(key, False))
    merged.condition_tainted = old.condition_tainted or new.condition_tainted
    merged.uncertain = old.uncertain or new.uncertain
    merged.reasons = set(old.reasons) | set(new.reasons)
    return merged, merged.signature() != old.signature()


def _operand_tainted(state: State, operand: str) -> bool:
    cleaned = _clean_operand(operand)
    if cleaned in REGISTER_NAMES:
        return bool(state.regs.get(cleaned, False))
    memory = _memory_key(cleaned)
    if memory is not None and memory in state.memory:
        return bool(state.memory[memory])
    return any(state.regs.get(reg, False) for reg in _register_tokens(cleaned))


def _set_register(state: State, register: str, tainted: bool) -> None:
    reg = register.upper()
    state.regs[reg] = tainted
    if reg == "EDX":
        state.regs["DL"] = tainted
    elif reg == "DL":
        # This analysis tracks only entry-DL influence. Replacing DL removes that
        # influence from the low byte and therefore from EDX as a whole unless the
        # new DL value is itself tainted.
        state.regs["EDX"] = tainted


def _write_operand(state: State, operand: str, tainted: bool) -> bool:
    cleaned = _clean_operand(operand)
    if cleaned in REGISTER_NAMES:
        _set_register(state, cleaned, tainted)
        return True
    memory = _memory_key(cleaned)
    if memory is not None:
        state.memory[memory] = tainted
        return True
    return False


def _mark_uncertain(state: State, instruction: dict[str, Any], reason: str) -> None:
    state.uncertain = True
    state.reasons.add(f"{instruction.get('address') or '?'} {instruction.get('mnemonic') or '?'}: {reason}")


def _conditional_jump(mnemonic: str) -> bool:
    upper = mnemonic.upper()
    return upper.startswith("J") and upper != "JMP"


def _successors(instruction: dict[str, Any], function_addresses: set[str]) -> list[str]:
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
    if _conditional_jump(mnemonic):
        result = list(flows)
        if fallthrough in function_addresses and fallthrough not in result:
            result.append(fallthrough)
        return result
    if fallthrough in function_addresses:
        return [fallthrough]
    return []


def _analyze_function(row: dict[str, Any]) -> dict[str, Any]:
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
            "name": function.get("name"),
            "instruction_count": 0,
            "analysis_complete": False,
            "entry_dl_observed": False,
            "entry_dl_controls_conditional_branch": False,
            "entry_dl_forwarded_to_release_backend": False,
            "condition_observations": [],
            "branch_observations": [],
            "bitwise_observations": [],
            "transfer_observations": [],
            "uncertainty_reasons": ["function has no instructions"],
        }

    in_states: dict[str, State] = {ordered[0]: _initial_state()}
    queue: deque[str] = deque([ordered[0]])
    condition_observations: dict[str, dict[str, Any]] = {}
    branch_observations: dict[str, dict[str, Any]] = {}
    bitwise_observations: dict[str, dict[str, Any]] = {}
    transfer_observations: dict[str, dict[str, Any]] = {}
    observed_tainted_read = False
    iterations = 0
    max_iterations = max(64, len(ordered) * 32)

    while queue:
        current = queue.popleft()
        iterations += 1
        if iterations > max_iterations:
            in_states[current].uncertain = True
            in_states[current].reasons.add("data-flow iteration limit reached")
            break
        instruction = by_address[current]
        state = in_states[current]
        out = state.copy()
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        operands = [str(value) for value in (instruction.get("operands") or [])]
        operand_taints = [_operand_tainted(state, operand) for operand in operands]
        if any(operand_taints):
            observed_tainted_read = True

        if mnemonic in {"TEST", "CMP"}:
            out.condition_tainted = any(operand_taints)
            if out.condition_tainted:
                condition_observations[current] = {
                    "instruction": current,
                    "mnemonic": mnemonic,
                    "operands": operands,
                    "entry_dl_influenced": True,
                }
        elif _conditional_jump(mnemonic):
            if state.condition_tainted:
                branch_observations[current] = {
                    "instruction": current,
                    "mnemonic": mnemonic,
                    "flows": [
                        target
                        for target in (_norm_address(value) for value in (instruction.get("flows") or []))
                        if target is not None
                    ],
                    "fallthrough": _norm_address(instruction.get("fallthrough")),
                    "entry_dl_influenced": True,
                }
            # Flags have been consumed; do not leak one comparison indefinitely.
            out.condition_tainted = False
        elif mnemonic == "MOV" and len(operands) == 2:
            if not _write_operand(out, operands[0], operand_taints[1]):
                _mark_uncertain(out, instruction, "unsupported MOV destination")
        elif mnemonic in {"MOVZX", "MOVSX"} and len(operands) == 2:
            if not _write_operand(out, operands[0], operand_taints[1]):
                _mark_uncertain(out, instruction, f"unsupported {mnemonic} destination")
        elif mnemonic == "LEA" and len(operands) == 2:
            if not _write_operand(out, operands[0], operand_taints[1]):
                _mark_uncertain(out, instruction, "unsupported LEA destination")
        elif mnemonic == "XOR" and len(operands) == 2 and _clean_operand(operands[0]) == _clean_operand(operands[1]):
            if not _write_operand(out, operands[0], False):
                _mark_uncertain(out, instruction, "unsupported XOR-zero destination")
            if any(operand_taints):
                bitwise_observations[current] = {
                    "instruction": current,
                    "mnemonic": mnemonic,
                    "operands": operands,
                    "entry_dl_influenced_before_write": True,
                    "result_entry_dl_influenced": False,
                }
        elif mnemonic in BINARY_WRITE_MNEMONICS and len(operands) == 2:
            result_tainted = any(operand_taints)
            if not _write_operand(out, operands[0], result_tainted):
                _mark_uncertain(out, instruction, f"unsupported {mnemonic} destination")
            if result_tainted and mnemonic in BITWISE_MNEMONICS:
                bitwise_observations[current] = {
                    "instruction": current,
                    "mnemonic": mnemonic,
                    "operands": operands,
                    "entry_dl_influenced_before_write": True,
                    "result_entry_dl_influenced": True,
                }
        elif mnemonic.startswith("SET") and len(operands) == 1:
            if not _write_operand(out, operands[0], state.condition_tainted):
                _mark_uncertain(out, instruction, "unsupported SETcc destination")
        elif mnemonic == "PUSH" and len(operands) == 1:
            # Exact stack offsets are unnecessary here; the observation is retained
            # so later transfer analysis can see that entry DL reached a pushed value.
            if operand_taints[0]:
                key = f"push@{current}"
                out.memory[key] = True
        elif mnemonic == "POP" and len(operands) == 1:
            # Without exact ESP modeling we cannot pair arbitrary POPs safely.
            if not _write_operand(out, operands[0], False):
                _mark_uncertain(out, instruction, "unsupported POP destination")
        elif mnemonic in {"CALL", "JMP"}:
            target = _transfer_target(instruction)
            tainted_registers = [reg for reg in ("ECX", "EDX", "DL", "EAX") if state.regs.get(reg, False)]
            if tainted_registers:
                transfer_observations[current] = {
                    "instruction": current,
                    "transfer_kind": "tail-call" if mnemonic == "JMP" else "call",
                    "target": target,
                    "entry_dl_influenced_registers": tainted_registers,
                }
            if mnemonic == "CALL":
                _set_register(out, "EAX", False)
                _set_register(out, "ECX", False)
                _set_register(out, "EDX", False)
                out.condition_tainted = False
        elif mnemonic in {"NOP", "LEAVE"} or mnemonic.startswith("RET") or mnemonic.startswith("J"):
            pass
        else:
            # Only mark uncertainty when an unsupported instruction writes a register
            # that currently carries entry-DL influence or has a register destination.
            if operands and _clean_operand(operands[0]) in REGISTER_NAMES:
                destination = _clean_operand(operands[0])
                if state.regs.get(destination, False) or any(operand_taints):
                    _mark_uncertain(out, instruction, "instruction is outside modeled DL-taint subset")
                    _set_register(out, destination, False)

        for successor in _successors(instruction, set(by_address)):
            merged, changed = _merge_state(in_states.get(successor), out)
            if changed:
                in_states[successor] = merged
                queue.append(successor)

    all_reasons = sorted({reason for state in in_states.values() for reason in state.reasons})
    transfers = [transfer_observations[key] for key in sorted(transfer_observations)]
    forwarded_to_release_backend = any(
        item.get("target") == RELEASE_BACKEND and "DL" in item.get("entry_dl_influenced_registers", [])
        for item in transfers
    )
    return {
        "address": address,
        "name": function.get("name"),
        "calling_convention": function.get("calling_convention"),
        "instruction_count": len(instructions),
        "reachable_instruction_count": len(in_states),
        "analysis_complete": not all_reasons,
        "entry_dl_observed": observed_tainted_read,
        "entry_dl_controls_conditional_branch": bool(branch_observations),
        "entry_dl_bitwise_transformed": bool(bitwise_observations),
        "entry_dl_forwarded_to_any_transfer": bool(transfers),
        "entry_dl_forwarded_to_release_backend": forwarded_to_release_backend,
        "condition_observations": [condition_observations[key] for key in sorted(condition_observations)],
        "branch_observations": [branch_observations[key] for key in sorted(branch_observations)],
        "bitwise_observations": [bitwise_observations[key] for key in sorted(bitwise_observations)],
        "transfer_observations": transfers,
        "uncertainty_reasons": all_reasons,
    }


def analyze_release_byte_behavior(instruction_export: Path) -> dict[str, Any]:
    rows = _load_rows(instruction_export)
    functions = [_analyze_function(rows[address]) for address in TARGETS]
    by_address = {row["address"]: row for row in functions}
    thunk = by_address[THUNK]
    backend = by_address[RELEASE_BACKEND]
    return {
        "format": FORMAT,
        "instruction_export": str(instruction_export),
        "functions": functions,
        "thunk_entry_dl_forwarded_to_release_backend": thunk["entry_dl_forwarded_to_release_backend"],
        "release_backend_entry_dl_observed": backend["entry_dl_observed"],
        "release_backend_entry_dl_controls_conditional_branch": backend["entry_dl_controls_conditional_branch"],
        "release_backend_entry_dl_bitwise_transformed": backend["entry_dl_bitwise_transformed"],
        "analysis_complete": all(row["analysis_complete"] for row in functions),
        "scope": {
            "entry_dl_behavior_observed": bool(thunk["entry_dl_observed"] or backend["entry_dl_observed"]),
            "entry_dl_forwarding_observed": thunk["entry_dl_forwarded_to_release_backend"],
            "entry_dl_control_flow_influence_observed": backend["entry_dl_controls_conditional_branch"],
            "entry_dl_bitwise_influence_observed": backend["entry_dl_bitwise_transformed"],
            "release_flag_role_proven": False,
            "delete_kind_role_proven": False,
            "destructor_policy_proven": False,
            "operator_delete_identity_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "This artifact records instruction-level influence of the release-path entry "
                "DL byte. Even branch or bitwise influence does not identify the byte as a "
                "delete/release flag without an independent semantic anchor."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_release_byte_behavior(args.instruction_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"analysis complete: {report['analysis_complete']}")
    print(f"thunk DL forwarded: {report['thunk_entry_dl_forwarded_to_release_backend']}")
    print(f"backend DL observed: {report['release_backend_entry_dl_observed']}")
    print(f"backend DL controls branch: {report['release_backend_entry_dl_controls_conditional_branch']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

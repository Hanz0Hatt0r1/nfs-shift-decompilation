#!/usr/bin/env python3
"""Classify implicit push/pop and normalized ESP carriers from base/index writable .data loads."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_fun005ffc50_base_indexed_data_stack_spill_reload.py"
FORMAT = "SHIFT.P1B.HDVehicle4330BaseIndexedImplicitStackCarrierSurface/1"
SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
WINDOW = 16


def upstream_module():
    spec = importlib.util.spec_from_file_location("p1a_base_index_stack", UPSTREAM_TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def direct_target(operand: str):
    return int(operand, 16) if re.fullmatch(r"0x[0-9a-fA-F]+", operand) else None


def scan_rows(rows, up=None):
    up = up or upstream_module()
    rows = list(rows)
    addr_state = {}
    active = []
    loads = []
    pushes = []
    pops = []
    normalized = []
    transfers = []
    escapes = []
    terms = Counter()

    for address, mnemonic, operands in rows:
        parts = operands.split(",") if operands else []
        new_active = []
        for state in active:
            state["age"] += 1

            if mnemonic in {"call", "jmp"}:
                if operands in state["regs"]:
                    transfers.append(
                        {
                            "load_site": f"0x{state['load']:08x}",
                            "effective_address": f"0x{state['ea']:08x}",
                            "transfer_site": f"0x{address:08x}",
                            "kind": mnemonic,
                            "transfer_register": operands,
                            "distance": state["age"],
                            "transformed": state["regs"][operands],
                        }
                    )
                    terms["matched_transfer"] += 1
                else:
                    target = direct_target(operands)
                    if mnemonic == "call" and target is not None:
                        for push in state["pending_pushes"]:
                            escapes.append(
                                {
                                    **push,
                                    "call_site": f"0x{address:08x}",
                                    "direct_callee": f"0x{target:08x}",
                                }
                            )
                    terms["other_control_transfer"] += 1
                continue

            if mnemonic.startswith("j") or mnemonic.startswith("loop") or mnemonic in up.CONTROL_STOPS or mnemonic in {"ret", "retn"}:
                terms["other_control_transfer"] += 1
                continue

            regs = dict(state["regs"])
            stack = dict(state["stack"])
            esp_delta = state["esp_delta"]
            pending_pushes = list(state["pending_pushes"])
            handled = False

            if mnemonic == "push" and len(parts) == 1:
                handled = True
                esp_delta -= 4
                source = parts[0]
                if source in regs:
                    stack[esp_delta] = regs[source]
                    event = {
                        "load_site": f"0x{state['load']:08x}",
                        "effective_address": f"0x{state['ea']:08x}",
                        "push_site": f"0x{address:08x}",
                        "source_register": source,
                        "canonical_esp_offset": esp_delta,
                        "transformed": regs[source],
                        "distance": state["age"],
                    }
                    pushes.append(event)
                    pending_pushes.append(event)
                else:
                    stack.pop(esp_delta, None)

            elif mnemonic == "pop" and len(parts) == 1:
                handled = True
                destination = parts[0]
                if destination in up.REGS:
                    if esp_delta in stack:
                        regs[destination] = stack[esp_delta]
                        pops.append(
                            {
                                "load_site": f"0x{state['load']:08x}",
                                "effective_address": f"0x{state['ea']:08x}",
                                "pop_site": f"0x{address:08x}",
                                "destination_register": destination,
                                "canonical_esp_offset": esp_delta,
                                "transformed": stack[esp_delta],
                                "distance": state["age"],
                            }
                        )
                    else:
                        regs.pop(destination, None)
                stack.pop(esp_delta, None)
                esp_delta += 4

            elif mnemonic in {"add", "sub"} and len(parts) == 2 and parts[0] == "esp":
                handled = True
                amount = up.parse_imm(parts[1])
                if amount is None:
                    stack.clear()
                    esp_delta = 0
                else:
                    esp_delta += amount if mnemonic == "add" else -amount
                    normalized.append(
                        {
                            "load_site": f"0x{state['load']:08x}",
                            "adjust_site": f"0x{address:08x}",
                            "mnemonic": mnemonic,
                            "amount": amount,
                            "canonical_esp_delta": esp_delta,
                            "distance": state["age"],
                        }
                    )

            elif mnemonic == "mov" and len(parts) == 2 and parts[0] in up.REGS and parts[1] in up.REGS:
                handled = True
                destination, source = parts
                if source in regs:
                    regs[destination] = regs[source]
                else:
                    regs.pop(destination, None)

            elif mnemonic == "xchg" and len(parts) == 2 and parts[0] in up.REGS and parts[1] in up.REGS:
                handled = True
                left, right = parts
                left_value = regs.pop(left, None)
                right_value = regs.pop(right, None)
                if left_value is not None:
                    regs[right] = left_value
                if right_value is not None:
                    regs[left] = right_value

            elif mnemonic in up.DEST_DEP and parts and parts[0] in up.REGS:
                handled = True
                destination = parts[0]
                if destination in regs:
                    erase = (
                        len(parts) >= 2
                        and parts[1] == destination
                        and mnemonic in {"xor", "sub"}
                    ) or (
                        len(parts) >= 2
                        and parts[1] in {"0", "0x0"}
                        and mnemonic == "and"
                    )
                    if erase:
                        regs.pop(destination, None)
                    else:
                        regs[destination] = True
                elif up.writes_reg(mnemonic, operands, destination):
                    regs.pop(destination, None)

            elif mnemonic == "imul" and len(parts) >= 2 and parts[0] in up.REGS:
                handled = True
                destination, source = parts[0], parts[1]
                if source in regs:
                    regs[destination] = True
                else:
                    regs.pop(destination, None)

            elif mnemonic == "lea" and len(parts) == 2 and parts[0] in up.REGS:
                handled = True
                destination, source = parts
                refs = [
                    reg
                    for reg in up.REGS
                    if re.search(r"(?<![a-z0-9])" + reg + r"(?![a-z0-9])", source)
                    and reg in regs
                ]
                if refs:
                    regs[destination] = True
                else:
                    regs.pop(destination, None)

            if not handled:
                if parts and parts[0] in {"esp", "sp"} and mnemonic not in up.READ_ONLY_FIRST:
                    stack.clear()
                    esp_delta = 0
                for reg in list(regs):
                    if up.writes_reg(mnemonic, operands, reg):
                        regs.pop(reg, None)

            if not regs and not stack:
                terms["all_taint_dead"] += 1
                continue
            if state["age"] >= WINDOW:
                terms["window_exhausted"] += 1
                continue

            state.update(
                regs=regs,
                stack=stack,
                esp_delta=esp_delta,
                pending_pushes=pending_pushes,
            )
            new_active.append(state)

        active = new_active
        load = up.parse_load(mnemonic, operands, up.state_values(addr_state))
        if load:
            register, effective_address, source = load
            loads.append((address, register, effective_address, source))
            active.append(
                {
                    "load": address,
                    "ea": effective_address,
                    "regs": {register: False},
                    "stack": {},
                    "esp_delta": 0,
                    "age": 0,
                    "pending_pushes": [],
                }
            )
        addr_state = up.update_state(mnemonic, operands, addr_state)

    return {
        "decoded_instruction_count": len(rows),
        "base_indexed_data_load_count": len(loads),
        "unique_effective_address_count": len({row[2] for row in loads}),
        "implicit_push_event_count": len(pushes),
        "implicit_pop_reload_event_count": len(pops),
        "normalized_esp_adjust_event_count": len(normalized),
        "tainted_register_indirect_transfer_count": len(transfers),
        "direct_call_argument_escape_count": len(escapes),
        "direct_call_argument_escapes": escapes,
        "termination_reason_counts": dict(sorted(terms.items())),
    }


def analyze(executable: Path):
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if digest != SHA:
        raise ValueError(digest)
    up = upstream_module()
    result = scan_rows(up.dis(executable), up)
    expected = (2847850, 63, 51, 5, 0, 0, 0, 5)
    actual = (
        result["decoded_instruction_count"],
        result["base_indexed_data_load_count"],
        result["unique_effective_address_count"],
        result["implicit_push_event_count"],
        result["implicit_pop_reload_event_count"],
        result["normalized_esp_adjust_event_count"],
        result["tainted_register_indirect_transfer_count"],
        result["direct_call_argument_escape_count"],
    )
    if actual != expected:
        raise AssertionError(("surface drift", actual, result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.executable)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

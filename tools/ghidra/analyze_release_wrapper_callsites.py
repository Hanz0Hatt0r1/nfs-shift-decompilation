#!/usr/bin/env python3
"""Recover physical argument sources at direct release-wrapper callsites.

The exact callsites come from SHIFT-MEMORY-RELEASE-WRAPPER-CALLERS/1. Caller
instruction bodies are interpreted with the same fail-closed symbolic x86 engine
used by memory-wrapper forwarding. No Ghidra decompiler parameter types are used.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-MEMORY-RELEASE-WRAPPER-CALLSITES/1"
INVENTORY_FORMAT = "SHIFT-MEMORY-RELEASE-WRAPPER-CALLERS/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/1"
WRAPPER_STORAGE = {
    "0x00886930": ["ECX:4", "DL:1", "Stack[0x4]:4"],
    "0x00886950": ["ECX:4", "DL:1", "Stack[0x4]:4", "Stack[0x8]:4"],
}
WRAPPER_NAMES = {
    "0x00886930": "FUN_00886930",
    "0x00886950": "FUN_00886950",
}
ENTRY_STACK_OFFSETS = tuple(range(0x4, 0x44, 4))
LOW8_CONSTANT = re.compile(r"^low8\(constant:0x([0-9a-f]+)\)$")
DIRECT_CONSTANT = re.compile(r"^constant:0x([0-9a-f]+)$")


def _load_engine():
    path = Path(__file__).with_name("analyze_memory_wrapper_forwarding.py")
    spec = importlib.util.spec_from_file_location("_shift_memory_forwarding_engine", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load symbolic forwarding engine: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def _load_inventory(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != INVENTORY_FORMAT:
        raise ValueError(f"{path}: expected {INVENTORY_FORMAT}")
    return value


def _load_instruction_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved caller target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict):
            raise ValueError(f"{path}: function record missing")
        address = _norm_address(function.get("address"))
        if address is None:
            raise ValueError(f"{path}: invalid function address")
        rows[address] = row
    return rows


def _caller_entry_spec() -> dict[str, Any]:
    storage = ["ECX:4", "EDX:4"]
    storage.extend(f"Stack[0x{offset:x}]:4" for offset in ENTRY_STACK_OFFSETS)
    return {"input_storage": storage}


def _states_before_instructions(engine, row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    instructions = [item for item in (row.get("instructions") or []) if isinstance(item, dict)]
    by_address = {
        address: item
        for item in instructions
        if (address := engine._norm_address(item.get("address"))) is not None
    }
    ordered = sorted(by_address)
    if not ordered:
        return {}, by_address
    states = {ordered[0]: engine._initial_state(_caller_entry_spec())}
    queue: deque[str] = deque([ordered[0]])
    iterations = 0
    max_iterations = max(64, len(ordered) * 32)
    while queue:
        current = queue.popleft()
        iterations += 1
        if iterations > max_iterations:
            states[current].uncertain = True
            states[current].reasons.add("data-flow iteration limit reached")
            break
        instruction = by_address[current]
        out = engine._transfer(states[current], instruction)
        for successor in engine._successors(instruction, set(by_address)):
            merged, changed = engine._merge_state(states.get(successor), out)
            if changed:
                states[successor] = merged
                queue.append(successor)
    return states, by_address


def _wrapper_arguments(engine, state, wrapper_address: str) -> list[dict[str, Any]]:
    pseudo_backend = {
        "parameter_storage": WRAPPER_STORAGE[wrapper_address],
    }
    return engine._backend_arguments(state, pseudo_backend)


def _argument(arguments: list[dict[str, Any]], storage: str) -> dict[str, Any] | None:
    return next(
        (item for item in arguments if isinstance(item, dict) and item.get("storage") == storage),
        None,
    )


def _dl_constant(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    match = LOW8_CONSTANT.match(value)
    if match:
        return int(match.group(1), 16) & 0xFF
    match = DIRECT_CONSTANT.match(value)
    if match:
        return int(match.group(1), 16) & 0xFF
    return None


def _callsite_record(engine, caller: dict[str, Any], call: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    states, by_address = _states_before_instructions(engine, row)
    instruction_address = _norm_address(call.get("instruction"))
    wrapper_address = _norm_address(call.get("wrapper_address"))
    instruction = by_address.get(instruction_address or "")
    state = states.get(instruction_address or "")
    reasons: list[str] = []
    if instruction is None:
        reasons.append("callgraph instruction is absent from targeted caller export")
    if wrapper_address not in WRAPPER_STORAGE:
        reasons.append("callgraph target is not a modeled release wrapper")
    if state is None:
        reasons.append("call instruction has no reachable symbolic state")

    arguments: list[dict[str, Any]] = []
    mnemonic = str((instruction or {}).get("mnemonic") or "").upper()
    if instruction is not None and mnemonic != "CALL":
        reasons.append(f"release-wrapper edge uses unsupported transfer mnemonic {mnemonic or '?'}")
    if state is not None and wrapper_address in WRAPPER_STORAGE and mnemonic == "CALL":
        arguments = _wrapper_arguments(engine, state, wrapper_address)
        if state.uncertain:
            reasons.extend(sorted(state.reasons))
        if not all(item.get("resolved") is True for item in arguments):
            reasons.append("one or more physical wrapper arguments are unresolved")

    ecx = _argument(arguments, "ECX:4")
    dl = _argument(arguments, "DL:1")
    stack_pointer = _argument(arguments, "Stack[0x4]:4")
    ecx_source = ecx.get("source") if isinstance(ecx, dict) else None
    dl_source = dl.get("source") if isinstance(dl, dict) else None
    pointer_source = stack_pointer.get("source") if isinstance(stack_pointer, dict) else None
    resolved = bool(arguments and not reasons)
    duplicate_pointer = bool(
        resolved
        and isinstance(ecx_source, str)
        and isinstance(pointer_source, str)
        and ecx_source != engine.UNKNOWN
        and ecx_source == pointer_source
    )
    return {
        "caller": caller.get("address"),
        "instruction": instruction_address,
        "wrapper": WRAPPER_NAMES.get(wrapper_address or "", call.get("wrapper")),
        "wrapper_address": wrapper_address,
        "transfer_mnemonic": mnemonic or None,
        "arguments": arguments,
        "arguments_resolved": resolved,
        "incoming_state_uncertain": bool(state.uncertain) if state is not None else True,
        "ecx_source": ecx_source,
        "dl_source": dl_source,
        "dl_constant_low8": _dl_constant(dl_source),
        "released_pointer_candidate_source": pointer_source,
        "ecx_matches_stack_pointer_source": duplicate_pointer,
        "uncertainty_reasons": sorted(set(reasons)),
    }


def analyze_release_wrapper_callsites(
    inventory_path: Path,
    instruction_export: Path,
) -> dict[str, Any]:
    inventory = _load_inventory(inventory_path)
    rows = _load_instruction_rows(instruction_export)
    engine = _load_engine()

    caller_rows = [row for row in (inventory.get("callers") or []) if isinstance(row, dict)]
    sites: list[dict[str, Any]] = []
    missing_callers: list[str] = []
    for caller in caller_rows:
        address = _norm_address(caller.get("address"))
        row = rows.get(address or "")
        if row is None:
            if address:
                missing_callers.append(address)
            continue
        for call in caller.get("calls") or []:
            if isinstance(call, dict):
                sites.append(_callsite_record(engine, caller, call, row))

    sites.sort(key=lambda item: (item.get("caller") or "", item.get("instruction") or ""))
    resolved_sites = [site for site in sites if site["arguments_resolved"] is True]
    dl_counter = Counter(
        str(site["dl_source"])
        for site in resolved_sites
        if isinstance(site.get("dl_source"), str)
    )
    dl_constant_counter = Counter(
        int(site["dl_constant_low8"])
        for site in resolved_sites
        if site.get("dl_constant_low8") is not None
    )
    duplicate_count = sum(site["ecx_matches_stack_pointer_source"] is True for site in resolved_sites)

    return {
        "format": FORMAT,
        "caller_inventory": str(inventory_path),
        "instruction_export": str(instruction_export),
        "inventory_truncated": inventory.get("truncated") is True,
        "selected_caller_count": inventory.get("selected_caller_count"),
        "exported_caller_count": len(rows),
        "missing_caller_exports": sorted(missing_callers),
        "callsite_count": len(sites),
        "resolved_callsite_count": len(resolved_sites),
        "all_selected_callsites_resolved": bool(sites) and len(resolved_sites) == len(sites) and not missing_callers,
        "dl_source_histogram": [
            {"source": source, "count": count}
            for source, count in sorted(dl_counter.items())
        ],
        "dl_constant_low8_histogram": [
            {"value": value, "count": count}
            for value, count in sorted(dl_constant_counter.items())
        ],
        "ecx_stack_pointer_duplicate_count": duplicate_count,
        "ecx_stack_pointer_duplicate_fraction": (
            duplicate_count / len(resolved_sites) if resolved_sites else None
        ),
        "callsites": sites,
        "scope": {
            "direct_callgraph_sites_used": True,
            "targeted_caller_instruction_dataflow_used": True,
            "ghidra_decompiler_parameter_types_used": False,
            "release_wrapper_argument_forwarding_observed": bool(resolved_sites),
            "release_byte_value_distribution_observed": bool(dl_counter),
            "release_byte_role_proven": False,
            "release_flag_role_proven": False,
            "delete_kind_role_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "Resolved callsites prove only machine-level values delivered to physical "
                "release-wrapper storage. Constant/distribution patterns and ECX/stack "
                "duplication do not assign semantic meaning to DL or the redundant ECX input."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_release_wrapper_callsites(args.inventory, args.instruction_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"callsites: {report['resolved_callsite_count']}/{report['callsite_count']}")
    print(f"DL sources: {len(report['dl_source_histogram'])}")
    print(f"ECX/stack pointer duplicates: {report['ecx_stack_pointer_duplicate_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Prove the retail Physics Manager scheduler entry without guessing cadence.

This stage joins the source-backed Physics Manager contract to raw SHIFT.exe
Ghidra exports.  It deliberately stops before claiming retail cadence: the
manager vtable +0x18 entry and the exact direct chain down to FUN_00713050 can
be proven statically, while the external indirect invocation of that virtual
entry and the elapsed/accumulator value feeding the schedule still require an
instruction/reference proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.RetailOuterUpdateSchedulerFrontier/1"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
MANAGER_FORMAT = "SHIFT.PhysicsManagerRuntime/1"
MANAGER_VTABLE_SYMBOL = "PTR_FUN_00b04524"
MANAGER_VTABLE = 0x00B04524
MANAGER_SCHEDULER_SLOT_OFFSET = 0x18
MANAGER_SCHEDULER_ENTRY = 0x00711B50
MANAGER_RELEASE_SLOT_OFFSET = 0x1C
MANAGER_RELEASE_ENTRY = 0x0070FFB0
MANAGER_ACCESSOR = 0x0070FE90
MANAGER_GET_ASSET_DATABASE = 0x00710870

EXPECTED_FUNCTIONS: dict[int, tuple[str, str]] = {
    0x00711B50: ("FUN_00711b50", "d4fdc3eb2a9e34f05e756d927bfe2177a0ba416173a54d84ff516a0fed0029d8"),
    0x007119C0: ("FUN_007119c0", "59d4eb983ba1644078fed51800755cdceebf6fc7dacda6390cd587319e176dc2"),
    0x007117E0: ("FUN_007117e0", "499d7057f793b98ea406aa8d4e7df827f138763d2624a5dd48a29290deca576f"),
}

# Exact direct bridge from the manager virtual entry to the already-audited
# upper outer-update scheduler boundary.  Four calls in FUN_0070f940 are kept
# distinct because call multiplicity is part of the static topology.
EXPECTED_EDGES: tuple[tuple[int, int, tuple[int, ...]], ...] = (
    (0x00711B50, 0x007119C0, (0x00711B76,)),
    (0x007119C0, 0x007117E0, (0x00711A6C,)),
    (0x007117E0, 0x0070F940, (0x0071196B,)),
    (0x0070F940, 0x007155E0, (0x0070F95B, 0x0070F977, 0x0070F993, 0x0070F9AF)),
    (0x007155E0, 0x0048ED52, (0x007155E3,)),
    (0x0048ED52, 0x007155E9, (0x0048ED58,)),
    (0x007155E9, 0x00715380, (0x00715602,)),
    (0x00715380, 0x00713050, (0x00715434,)),
)


def _norm(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    try:
        return int(token, 16) if token.startswith("0x") else int(token, 16)
    except ValueError:
        return None


def _hex(value: int) -> str:
    return f"0x{value:08x}"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: expected JSON object")
        rows.append(value)
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _binary_identity(binary: dict[str, Any]) -> dict[str, Any]:
    md5 = str(binary.get("md5") or binary.get("MD5") or "").lower()
    if md5 != PE_MD5:
        raise ValueError(f"retail PE MD5 drift: expected {PE_MD5}, got {md5 or '<missing>'}")
    return {"md5": md5, "verified": True}


def _validate_runtime_contract(source: str) -> dict[str, Any]:
    required = (
        f'MANAGER_FORMAT = "{MANAGER_FORMAT}"',
        f'MANAGER_VTABLE = "{MANAGER_VTABLE_SYMBOL}"',
        '"constructor": "FUN_0070fae0"',
        '"shutdown": "FUN_0070f580"',
    )
    missing = [token for token in required if token not in source]
    if missing:
        raise ValueError("Physics Manager runtime contract drift: " + ", ".join(missing))
    return {
        "format": MANAGER_FORMAT,
        "manager_vtable_symbol": MANAGER_VTABLE_SYMBOL,
        "constructor": "FUN_0070fae0",
        "shutdown": "FUN_0070f580",
        "verified": True,
    }


def _static_pointer(rows: Iterable[dict[str, Any]], address: int) -> int:
    matches = [row for row in rows if _norm(row.get("address")) == address]
    if len(matches) != 1:
        raise ValueError(f"static table address {_hex(address)} expected once; found {len(matches)}")
    row = matches[0]
    raw_hex = row.get("raw_hex")
    if not isinstance(raw_hex, str) or len(raw_hex) != 8:
        raise ValueError(f"static pointer {_hex(address)} is not one 32-bit raw value")
    try:
        raw = bytes.fromhex(raw_hex)
    except ValueError as exc:
        raise ValueError(f"static pointer {_hex(address)} has invalid raw_hex") from exc
    return int.from_bytes(raw, "little")


def _validate_vtable(static_rows: list[dict[str, Any]], global_rows: list[dict[str, Any]]) -> dict[str, Any]:
    symbols = [row for row in global_rows if _norm(row.get("address")) == MANAGER_VTABLE]
    if len(symbols) != 1 or symbols[0].get("name") != MANAGER_VTABLE_SYMBOL:
        raise ValueError("source-backed Physics Manager vtable symbol drift")

    scheduler_slot = MANAGER_VTABLE + MANAGER_SCHEDULER_SLOT_OFFSET
    release_slot = MANAGER_VTABLE + MANAGER_RELEASE_SLOT_OFFSET
    scheduler_target = _static_pointer(static_rows, scheduler_slot)
    release_target = _static_pointer(static_rows, release_slot)
    if scheduler_target != MANAGER_SCHEDULER_ENTRY:
        raise ValueError(
            f"Physics Manager +0x18 target drift: expected {_hex(MANAGER_SCHEDULER_ENTRY)}, "
            f"got {_hex(scheduler_target)}"
        )
    if release_target != MANAGER_RELEASE_ENTRY:
        raise ValueError(
            f"Physics Manager +0x1c release target drift: expected {_hex(MANAGER_RELEASE_ENTRY)}, "
            f"got {_hex(release_target)}"
        )
    return {
        "vtable": _hex(MANAGER_VTABLE),
        "vtable_symbol": MANAGER_VTABLE_SYMBOL,
        "scheduler_slot_offset": MANAGER_SCHEDULER_SLOT_OFFSET,
        "scheduler_slot_address": _hex(scheduler_slot),
        "scheduler_entry": _hex(scheduler_target),
        "release_slot_offset": MANAGER_RELEASE_SLOT_OFFSET,
        "release_slot_address": _hex(release_slot),
        "release_entry": _hex(release_target),
        "scheduler_entry_owner_proven": True,
    }


def _function_index(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        address = _norm(row.get("address"))
        if address is None:
            continue
        if address in result:
            raise ValueError(f"duplicate function row {_hex(address)}")
        result[address] = row
    return result


def _validate_function_fingerprints(functions: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for address, (name, digest) in EXPECTED_FUNCTIONS.items():
        row = functions.get(address)
        if row is None:
            raise ValueError(f"required scheduler function missing: {_hex(address)}")
        if row.get("name") != name:
            raise ValueError(f"scheduler function name drift at {_hex(address)}")
        if row.get("mnemonic_sha256") != digest:
            raise ValueError(f"scheduler function mnemonic hash drift at {_hex(address)}")
        result.append({
            "address": _hex(address),
            "name": name,
            "mnemonic_sha256": digest,
            "verified": True,
        })
    return result


def _edge_rows(callgraph: list[dict[str, Any]], source: int, target: int) -> list[dict[str, Any]]:
    return [
        row for row in callgraph
        if _norm(row.get("from_function")) == source
        and _norm(row.get("to")) == target
        and row.get("indirect") is False
    ]


def _validate_direct_chain(callgraph: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source, target, expected_calls in EXPECTED_EDGES:
        rows = _edge_rows(callgraph, source, target)
        instructions = sorted(
            value for value in (_norm(row.get("instruction")) for row in rows)
            if value is not None
        )
        if tuple(instructions) != expected_calls:
            raise ValueError(
                f"direct scheduler edge {_hex(source)} -> {_hex(target)} drift: "
                f"expected {[ _hex(x) for x in expected_calls ]}, "
                f"got {[ _hex(x) for x in instructions ]}"
            )
        result.append({
            "from": _hex(source),
            "to": _hex(target),
            "call_instructions": [_hex(value) for value in instructions],
            "direct": True,
            "verified": True,
        })
    return result


def _direct_incoming(callgraph: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    return [
        row for row in callgraph
        if _norm(row.get("to")) == target and row.get("indirect") is False
    ]


def _validate_accessor_anchor(callgraph: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _edge_rows(callgraph, MANAGER_GET_ASSET_DATABASE, MANAGER_ACCESSOR)
    if len(rows) != 1 or _norm(rows[0].get("instruction")) != 0x00710871:
        raise ValueError("cPhysicsManager GetAssetDatabase -> manager accessor anchor drift")
    return {
        "method_anchor": _hex(MANAGER_GET_ASSET_DATABASE),
        "manager_accessor": _hex(MANAGER_ACCESSOR),
        "call_instruction": "0x00710871",
        "verified": True,
    }


def build_frontier(
    binary_path: Path,
    functions_path: Path,
    callgraph_path: Path,
    static_tables_path: Path,
    globals_path: Path,
    physics_runtime_path: Path,
) -> dict[str, Any]:
    binary = _read_json(binary_path)
    functions = _function_index(_read_jsonl(functions_path))
    callgraph = _read_jsonl(callgraph_path)
    static_rows = _read_jsonl(static_tables_path)
    global_rows = _read_jsonl(globals_path)
    runtime_source = physics_runtime_path.read_text(encoding="utf-8")

    binary_identity = _binary_identity(binary)
    runtime_contract = _validate_runtime_contract(runtime_source)
    manager_vtable = _validate_vtable(static_rows, global_rows)
    fingerprints = _validate_function_fingerprints(functions)
    direct_chain = _validate_direct_chain(callgraph)
    accessor = _validate_accessor_anchor(callgraph)

    direct_incoming = _direct_incoming(callgraph, MANAGER_SCHEDULER_ENTRY)
    if direct_incoming:
        raise ValueError(
            "Physics Manager +0x18 scheduler entry unexpectedly acquired a direct caller; "
            "indirect-dispatch frontier must be re-audited"
        )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "blocked-indirect-entry-proof",
        "ready": False,
        "binary_identity": binary_identity,
        "physics_manager_contract": runtime_contract,
        "physics_manager_vtable": manager_vtable,
        "manager_accessor_anchor": accessor,
        "scheduler_entry_function_fingerprints": fingerprints,
        "direct_scheduler_chain": {
            "verified": True,
            "path": [
                "0x00711b50", "0x007119c0", "0x007117e0", "0x0070f940",
                "0x007155e0", "0x0048ed52", "0x007155e9", "0x00715380",
                "0x00713050",
            ],
            "edges": direct_chain,
            "terminates_at_existing_outer_update_scheduler_boundary": True,
        },
        "external_dispatch": {
            "scheduler_entry_has_direct_incoming_call": False,
            "indirect_invocation_callsite_proven": False,
            "manager_receiver_alias_at_invocation_proven": False,
            "entry_invocation_cadence_proven": False,
        },
        "cadence": {
            "retail_cadence_admitted": False,
            "host_1_60_is_retail_evidence": False,
            "rendered_frame_equivalence_proven": False,
            "manager_entry_elapsed_or_accumulator_input_proven": False,
        },
        "blocking_reasons": [
            "physics-manager-vtable-plus-0x18-indirect-invocation-callsite-not-proven",
            "physics-manager-scheduler-entry-elapsed-or-accumulator-input-not-proven",
        ],
        "next_static_targets": {
            "instruction_export_addresses": [
                "0x00711b50", "0x007119c0", "0x007117e0",
            ],
            "reference_targets": [
                "0x00b04524", "0x00b0453c",
            ],
            "question": (
                "prove the exact indirect caller/receiver of cPhysicsManager vtable +0x18 "
                "and trace the entry value that feeds the accumulator-driven FUN_00713050 schedule"
            ),
        },
        "limits": {
            "manager_slot_named_update": False,
            "host_pacing_promoted": False,
            "callgraph_adjacency_promoted_to_cadence": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("functions", type=Path)
    parser.add_argument("callgraph", type=Path)
    parser.add_argument("static_tables", type=Path)
    parser.add_argument("globals", type=Path)
    parser.add_argument("physics_runtime", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_frontier(
        args.binary,
        args.functions,
        args.callgraph,
        args.static_tables,
        args.globals,
        args.physics_runtime,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

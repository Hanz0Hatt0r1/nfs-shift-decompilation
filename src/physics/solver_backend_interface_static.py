"""Static contract for the two retail solver-backend interface objects.

The contract resolves the two previously unknown indirect calls in FUN_007b3f40
without assigning class names.  It combines the recovered retail source, exact
PE vtable bytes, constructor instruction previews from the existing Ghidra
export, and the already proven BODY/SDF callgraph.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.SolverBackendInterfaceStatic/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
EXECUTABLE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

BACKENDS: tuple[dict[str, Any], ...] = (
    {
        "registry_index": 0,
        "static_object": "0x00c23da8",
        "initializer": "FUN_007d2f70",
        "vtable": "0x00b0fc5c",
        "vtable_sha256": "bbf48672e1e4d11856470b65eed8ed441414ed895e9e26b3fc2fe1680220cbcf",
        "slots": (
            "0x007d3120",
            "0x007d2eb0",
            "0x007d2ec0",
            "0x007d2ed0",
            "0x007c6e30",
            "0x007c6e50",
            "0x007c7200",
            "0x007d3150",
            "0x007d43c0",
            "0x007d2ee0",
            "0x007d2ef0",
            "0x007d2f00",
        ),
        "selection_predicate_slot": 5,
        "selection_predicate": "FUN_007c6e50",
        "solve_slot": 6,
        "solve_target": "FUN_007c7200",
        "pre_solve_slot": 8,
        "pre_solve_target": "FUN_007d43c0",
    },
    {
        "registry_index": 1,
        "static_object": "0x00c23dac",
        "initializer": "FUN_007cd980",
        "vtable": "0x00b0fc8c",
        "vtable_sha256": "6e149f310297884875cd7df5af3123f08c31d92f5d363ab497b46997559b56f9",
        "slots": (
            "0x007d4870",
            "0x007d2f10",
            "0x007d2f20",
            "0x007d2f30",
            "0x007cdb20",
            "0x007cdb40",
            "0x007cdfc0",
            "0x007d48a0",
            "0x007d5600",
            "0x007d2f40",
            "0x007d2f50",
            "0x007d2f60",
        ),
        "selection_predicate_slot": 5,
        "selection_predicate": "FUN_007cdb40",
        "solve_slot": 6,
        "solve_target": "FUN_007cdfc0",
        "pre_solve_slot": 8,
        "pre_solve_target": "FUN_007d5600",
    },
)

FUNCTION_BYTES: dict[str, dict[str, Any]] = {
    "FUN_007d2e70": {
        "start": 0x007D2E70,
        "end": 0x007D2EA1,
        "sha256": "d4c46b08db0aacee5a65aa7210968ee30032a8d1867f7e18c8a3acf9ccd707cc",
    },
    "FUN_007d2f70": {
        "start": 0x007D2F70,
        "end": 0x007D3120,
        "sha256": "727cac680efaf5158d5a7a3262c7ee1e4a7459542cdb87356cb2e1bc87996817",
    },
    "FUN_007cd980": {
        "start": 0x007CD980,
        "end": 0x007CDAF4,
        "sha256": "8c866f7b8ea6eedd49df73243a928b4b7ce64a3e97e23fe027a985d8e681d209",
    },
}


def build_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "source": {
            "program": "SHIFT.exe",
            "executable_md5": EXECUTABLE_MD5,
            "decompile_sha256": SOURCE_SHA256,
            "evidence_kinds": [
                "recovered retail source",
                "exact retail PE vtable bytes",
                "existing Ghidra constructor instruction previews",
                "existing direct callgraph",
            ],
        },
        "registry": {
            "enumerator": "FUN_007d2e70",
            "indices": (0, 1),
            "index_0_result": "0x00c23da8",
            "index_1_result": "0x00c23dac",
            "other_result": None,
            "status": "proven-two-entry-static-object-registry",
        },
        "selection": {
            "function": "FUN_007b3820",
            "backend_field_offset": "0x48",
            "candidate_iteration": (0, 1),
            "predicate_vtable_offset": "0x14",
            "predicate_slot": 5,
            "predicate_input": "solver matrix pointer at owner+0x3c",
            "selected_pointer_write": "owner+0x48 = accepted static backend object",
            "fallback_when_none_selected": True,
            "promoted_method_name": False,
        },
        "dispatch": {
            "function": "FUN_007b3f40",
            "backend_field_offset": "0x48",
            "first_indirect_instruction": "0x007b3f8c",
            "first_vtable_offset": "0x20",
            "first_slot": 8,
            "first_exact_targets": (
                "FUN_007d43c0",
                "FUN_007d5600",
            ),
            "first_observed_role": (
                "selected backend pre-solve workspace reset/preparation before FUN_007b3ed0"
            ),
            "second_indirect_instruction": "0x007b4102",
            "second_vtable_offset": "0x18",
            "second_slot": 6,
            "second_exact_targets": (
                "FUN_007c7200",
                "FUN_007cdfc0",
            ),
            "second_observed_role": "selected backend solve kernel",
            "null_backend_fallback": "FUN_007b0f20",
            "virtual_target_set_closed": True,
        },
        "backend_candidates": BACKENDS,
        "support_slots": {
            "offset_0x04_slot_1": (
                "FUN_007d2eb0",
                "FUN_007d2f10",
            ),
            "offset_0x08_slot_2": (
                "FUN_007d2ec0",
                "FUN_007d2f20",
            ),
            "offset_0x0c_slot_3": (
                "FUN_007d2ed0",
                "FUN_007d2f30",
            ),
            "offset_0x2c_slot_11": (
                "FUN_007d2f00",
                "FUN_007d2f60",
            ),
            "note": (
                "FUN_007b3820 calls these slots after accepting a backend; this contract "
                "keeps their return-buffer/count semantics structural unless separately proven."
            ),
        },
        "vtable_export_gap": {
            "existing_maximal_candidate": "0x00b0fc2c",
            "missed_xref_started_subtables": (
                "0x00b0fc5c",
                "0x00b0fc8c",
            ),
            "reason": (
                "the existing Ghidra exporter advances to the end of a contiguous function-"
                "pointer run after emitting its first candidate, so directly referenced "
                "interior vptr starts can be skipped"
            ),
        },
        "closed_boundaries": {
            "FUN_007b3f40_first_indirect_target_set": True,
            "FUN_007b3f40_second_indirect_target_set": True,
            "backend_registry_cardinality": True,
            "backend_vptr_addresses": True,
            "backend_selection_predicate_slots": True,
            "null_backend_fallback": True,
        },
        "unknown": [
            "retail class/interface names for the two backend objects",
            "strong semantic names for support slots +0x04/+0x08/+0x0c/+0x2c",
            "whether external configuration can alter the two static object implementations",
        ],
        "scope": {
            "game_launched": False,
            "runtime_capture_used": False,
            "linux_runtime_implementation_changed": False,
            "automatic_function_renaming_performed": False,
        },
    }


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("format") != FORMAT:
        raise ValueError(f"expected {FORMAT}")
    source = contract.get("source") or {}
    if source.get("executable_md5") != EXECUTABLE_MD5:
        raise ValueError("unexpected executable identity")
    if source.get("decompile_sha256") != SOURCE_SHA256:
        raise ValueError("unexpected decompile identity")
    candidates = contract.get("backend_candidates")
    if not isinstance(candidates, tuple) or len(candidates) != 2:
        raise ValueError("exactly two backend candidates are required")
    for candidate in candidates:
        slots = candidate.get("slots")
        if not isinstance(slots, tuple) or len(slots) != 12:
            raise ValueError("each backend vtable must contain 12 proven slots")
        if slots[candidate["selection_predicate_slot"]] != "0x" + candidate["selection_predicate"][4:]:
            raise ValueError("selection predicate slot mismatch")
        if slots[candidate["solve_slot"]] != "0x" + candidate["solve_target"][4:]:
            raise ValueError("solve slot mismatch")
        if slots[candidate["pre_solve_slot"]] != "0x" + candidate["pre_solve_target"][4:]:
            raise ValueError("pre-solve slot mismatch")
    if any(value is not True for value in contract["closed_boundaries"].values()):
        raise ValueError("all advertised closed boundaries must remain proven")


def main() -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    contract = build_contract()
    validate_contract(contract)
    payload = json.dumps(contract, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

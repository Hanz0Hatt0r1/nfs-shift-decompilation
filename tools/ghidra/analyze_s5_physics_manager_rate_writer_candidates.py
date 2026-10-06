#!/usr/bin/env python3
"""Build a fail-closed cPhysicsManager +0x388 writer-candidate worklist.

This stage consumes only a bounded target-selection report and the generic
SHIFT.GhidraRegisterRelativeAccesses/1 syntactic access inventory produced from
that exact instruction slice.  A machine STORE at displacement +0x388 becomes a
candidate only.  Base-register object identity, cPhysicsManager membership,
value provenance, physical units and cadence all remain unproven.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.PhysicsManagerRateWriterWorklist/1"
SELECTION_FORMAT = "SHIFT.PhysicsManagerRateWriterTargetSelection/1"
ACCESS_FORMAT = "SHIFT.GhidraRegisterRelativeAccesses/1"
RATE_OFFSET = 0x388


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _norm(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("0x"):
        token = token[2:]
    try:
        return int(token, 16)
    except ValueError:
        return None


def _validate_selection(report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if report.get("status") != "bounded-discovery-targets-ready":
        raise ValueError("rate-writer target selection is not ready")
    scope = report.get("scope")
    if not isinstance(scope, Mapping):
        raise ValueError("target selection scope missing")
    forbidden_true = (
        "address_adjacency_proves_class_membership",
        "selected_function_is_cPhysicsManager_method",
        "selected_function_writes_plus_0x388",
        "field_semantics_proven",
        "physical_units_proven",
        "retail_cadence_admitted",
    )
    if any(scope.get(key) is not False for key in forbidden_true):
        raise ValueError("target selection unexpectedly promotes discovery semantics")

    targets = report.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("target selection contains no functions")
    if report.get("target_count") != len(targets):
        raise ValueError("target selection count drift")

    result: dict[str, Mapping[str, Any]] = {}
    for row in targets:
        if not isinstance(row, Mapping):
            raise ValueError("malformed target row")
        address = row.get("address")
        name = row.get("name")
        if not isinstance(address, str) or _norm(address) is None:
            raise ValueError("target address missing")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{address}: target name missing")
        if row.get("class_membership_proven") is not False:
            raise ValueError(f"{address}: target unexpectedly preclaims class membership")
        if address in result:
            raise ValueError(f"duplicate target {address}")
        result[address] = row
    return result


def analyze(selection_path: Path, accesses_path: Path) -> dict[str, Any]:
    selection = _load(selection_path, SELECTION_FORMAT)
    accesses = _load(accesses_path, ACCESS_FORMAT)
    targets = _validate_selection(selection)

    if accesses.get("base_register_filter") is not None:
        raise ValueError("rate-writer discovery requires an unfiltered base-register inventory")
    if accesses.get("function_count") != len(targets):
        raise ValueError(
            "register-relative inventory function_count does not match exact selected target set"
        )

    rows = accesses.get("accesses")
    if not isinstance(rows, list):
        raise ValueError("register-relative access rows missing")

    candidates: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("malformed register-relative access row")
        if row.get("displacement") != RATE_OFFSET:
            continue
        if row.get("access") not in {"write", "read-write"}:
            continue
        function = row.get("function")
        if not isinstance(function, str) or function not in targets:
            raise ValueError(
                f"+0x388 write references function outside exact target selection: {function!r}"
            )
        target = targets[function]
        candidates.append(
            {
                "function": function,
                "function_name": target["name"],
                "instruction": row.get("instruction"),
                "instruction_text": row.get("instruction_text"),
                "operand_index": row.get("operand_index"),
                "operand": row.get("operand"),
                "base_register": row.get("base_register"),
                "displacement": RATE_OFFSET,
                "displacement_hex": "0x388",
                "access": row.get("access"),
                "pcode_memory_ops": row.get("pcode_memory_ops"),
                "selected_by": target.get("selected_by"),
                "machine_store_candidate": True,
                "base_register_aliases_cPhysicsManager": False,
                "cPhysicsManager_plus_0x388_writer_proven": False,
                "stored_value_provenance_proven": False,
                "physical_units_proven": False,
                "field_semantics_proven": False,
            }
        )

    candidates.sort(
        key=lambda row: (
            str(row["function"]),
            str(row.get("instruction") or ""),
            int(row.get("operand_index") or 0),
        )
    )

    pcode_blockers = accesses.get("pcode_classification_blocker_count")
    unparsed = accesses.get("unparsed_memory_operand_count")
    if not isinstance(pcode_blockers, int) or not isinstance(unparsed, int):
        raise ValueError("register-relative completeness counters missing")
    selected_window_scan_complete = pcode_blockers == 0 and unparsed == 0
    candidate_worklist_ready = bool(candidates)

    blocking_reasons: list[str] = []
    if not candidates:
        blocking_reasons.append("no-simple-register-relative-plus-0x388-writer-candidate-in-selected-window")
    if not selected_window_scan_complete:
        blocking_reasons.append("selected-window-register-relative-scan-has-unparsed-or-pcode-blockers")
    blocking_reasons.extend(
        [
            "plus-0x388-candidate-base-register-object-alias-not-proven",
            "plus-0x388-store-value-provenance-not-proven",
            "plus-0x388-physical-units-not-proven",
            "retail-cadence-dynamic-multiplicity-not-proven",
        ]
    )

    return {
        "format": FORMAT,
        "ready": candidate_worklist_ready,
        "status": (
            "writer-candidate-worklist-ready"
            if candidate_worklist_ready and selected_window_scan_complete
            else "writer-candidate-worklist-ready-with-scan-blockers"
            if candidate_worklist_ready
            else "blocked-no-writer-candidate"
        ),
        "inputs": {
            "target_selection": str(selection_path),
            "register_relative_accesses": str(accesses_path),
        },
        "selection": {
            "window": selection.get("window"),
            "target_count": len(targets),
            "candidate_discovery_only": True,
        },
        "scan_completeness": {
            "selected_window_simple_register_relative_scan_complete": selected_window_scan_complete,
            "pcode_classification_blocker_count": pcode_blockers,
            "unparsed_memory_operand_count": unparsed,
            "full_program_writer_surface_complete": False,
            "reason": (
                "The selected window is a bounded candidate-discovery surface only; even a clean "
                "simple register-relative scan cannot exclude writers outside the target set."
            ),
        },
        "writer_candidate_count": len(candidates),
        "writer_candidate_function_count": len({row["function"] for row in candidates}),
        "writer_candidates": candidates,
        "adjudication": {
            "machine_plus_0x388_store_candidates_found": bool(candidates),
            "any_candidate_base_register_aliases_cPhysicsManager": False,
            "any_cPhysicsManager_plus_0x388_writer_proven": False,
            "plus_0x388_semantic_name_frequency": False,
            "plus_0x388_value_or_units_proven": False,
            "fixed_timestep_semantics_proven": False,
            "retail_cadence_admitted": False,
        },
        "blocking_reasons": sorted(set(blocking_reasons)),
        "next_exact_question": (
            "for each +0x388 machine STORE candidate, prove the base register aliases the "
            "source-backed cPhysicsManager instance at that instruction; only positive object "
            "writers may proceed to structured p-code stored-value provenance and physical units"
        ),
        "limits": {
            "address_proximity_used_as_class_membership": False,
            "register_name_used_as_this_identity": False,
            "candidate_store_promoted_to_object_writer": False,
            "frequency_name_promoted": False,
            "host_1_60_promoted": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_selection", type=Path)
    parser.add_argument("register_relative_accesses", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze(args.target_selection, args.register_relative_accesses)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print(f"ready: {str(report['ready']).lower()}")
    print(f"writer_candidates: {report['writer_candidate_count']}")
    print(
        "retail_cadence_admitted: "
        f"{str(report['adjudication']['retail_cadence_admitted']).lower()}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

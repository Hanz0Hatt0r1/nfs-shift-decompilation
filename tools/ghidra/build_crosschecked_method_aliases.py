#!/usr/bin/env python3
"""Promote exact method-name candidates only when repo contracts corroborate them.

`discover_method_name_anchors.py` intentionally emits semantic-name candidates,
not automatic renames. This tool adds a second independent evidence layer for a
small curated set whose exact function identities are already present in
reconstructed runtime contracts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.CrosscheckedMethodAliases/1"
ANCHOR_FORMAT = "SHIFT.GhidraMethodNameAnchors/1"

CROSSCHECKS: tuple[dict[str, Any], ...] = (
    {
        "subsystem": "physics",
        "address": "0x00710870",
        "alias": "MWL::Core::cPhysicsManager::GetAssetDatabase",
        "runtime_contract": "src/physics/physics_system_runtime.py",
        "required_contract_markers": (
            '"database_getter": "FUN_00710870"',
            '"load_call": "FUN_00640150(local_680, FUN_00710870(), 1)"',
        ),
        "independent_role": "physics asset-database getter",
    },
    {
        "subsystem": "physics",
        "address": "0x00714560",
        "alias": "MWL::Core::PhysicsParticipantManager::ChangeRaceMode",
        "runtime_contract": "src/physics/physics_participant_manager_event_runtime.py",
        "required_contract_markers": (
            '"consumer": "FUN_00714560"',
            '"dispatch_target": "FUN_00714560(&DAT_00c109e0, event)"',
        ),
        "independent_role": "PhysicsParticipantManager opcode-0x20 event consumer",
    },
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != ANCHOR_FORMAT:
        raise ValueError(f"{path}: expected {ANCHOR_FORMAT}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _function_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in payload.get("functions") or []:
        if not isinstance(row, dict):
            continue
        address = row.get("address")
        if isinstance(address, str):
            rows[address] = row
    return rows


def build_crosschecked_method_aliases(
    anchors_path: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    anchors = _load(anchors_path)
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    repo_root = repo_root.resolve()
    functions = _function_index(anchors)

    rows: list[dict[str, Any]] = []
    contract_inventory: dict[str, dict[str, Any]] = {}
    for spec in CROSSCHECKS:
        address = spec["address"]
        function = functions.get(address)
        contract_relative = str(spec["runtime_contract"])
        contract_path = repo_root / contract_relative
        contract_present = contract_path.is_file()
        contract_text = (
            contract_path.read_text(encoding="utf-8", errors="replace")
            if contract_present
            else ""
        )
        marker_checks = {
            marker: marker in contract_text
            for marker in spec["required_contract_markers"]
        }
        unique_candidate = (
            function.get("unique_method_name_candidate")
            if isinstance(function, dict)
            else None
        )
        checks = {
            "anchor_function_present": function is not None,
            "unique_method_anchor_status": bool(
                isinstance(function, dict)
                and function.get("status") == "unique-method-name-anchor-candidate"
            ),
            "exact_method_name": unique_candidate == spec["alias"],
            "runtime_contract_present": contract_present,
            "runtime_contract_markers": marker_checks,
        }
        promoted = bool(
            checks["anchor_function_present"]
            and checks["unique_method_anchor_status"]
            and checks["exact_method_name"]
            and checks["runtime_contract_present"]
            and all(marker_checks.values())
        )
        if contract_relative not in contract_inventory:
            contract_inventory[contract_relative] = {
                "path": contract_relative,
                "present": contract_present,
                "sha256": _sha256(contract_path) if contract_present else None,
            }
        rows.append(
            {
                "subsystem": spec["subsystem"],
                "address": address,
                "ghidra_name": function.get("name") if isinstance(function, dict) else None,
                "alias": spec["alias"],
                "independent_role": spec["independent_role"],
                "runtime_contract": contract_relative,
                "method_anchor_status": function.get("status") if isinstance(function, dict) else None,
                "anchor_string_addresses": (
                    function.get("anchor_string_addresses") or []
                    if isinstance(function, dict)
                    else []
                ),
                "promoted": promoted,
                "evidence_kind": "unique-exact-method-anchor-plus-runtime-contract",
                "checks": checks,
            }
        )

    rows.sort(key=lambda row: (row["subsystem"], row["address"]))
    promoted_rows = [row for row in rows if row["promoted"]]
    return {
        "format": FORMAT,
        "method_anchors": str(anchors_path),
        "repo_root": str(repo_root),
        "candidate_count": len(rows),
        "promoted_alias_count": len(promoted_rows),
        "failed_crosscheck_count": len(rows) - len(promoted_rows),
        "runtime_contracts": [contract_inventory[key] for key in sorted(contract_inventory)],
        "aliases": rows,
        "promoted_aliases": promoted_rows,
        "scope": {
            "unique_exact_method_anchors_used": True,
            "independent_runtime_contracts_used": True,
            "automatic_unanchored_renames_allowed": False,
            "ambiguous_method_anchors_promoted": False,
            "parameter_semantics_proven": False,
            "return_value_semantics_proven": False,
            "ownership_semantics_proven": False,
            "runtime_execution_proven": False,
            "note": (
                "Promotion requires the exact unique Ghidra method-name anchor and "
                "independent function-identity markers already present in a recovered "
                "runtime contract. This corroborates the semantic alias but does not "
                "prove parameters, return values, ownership or execution on a given path."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method_anchors", type=Path, help=f"{ANCHOR_FORMAT} JSON")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="return non-zero if any curated alias fails its independent cross-check",
    )
    args = parser.parse_args()

    report = build_crosschecked_method_aliases(args.method_anchors, args.repo_root)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"candidates: {report['candidate_count']}")
    print(f"promoted aliases: {report['promoted_alias_count']}")
    print(f"failed cross-checks: {report['failed_crosscheck_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.fail_on_mismatch and report["failed_crosscheck_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

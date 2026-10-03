#!/usr/bin/env python3
"""Build a conservative runtime-facing manifest for the retail memory wrappers.

The manifest preserves the recovered wrapper identities and physical entry
storage from SHIFT-MEMORY-WRAPPER-FORWARDING/1. Parameter names are promoted
only through the canonical ``memory_pool_runtime`` evidence gate, which requires
independent static physical-role and source semantic summaries. Unproven
parameters remain ``argN`` and no complete helper ABI is claimed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

FORMAT = "SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1"
FORWARDING_FORMAT = "SHIFT-MEMORY-WRAPPER-FORWARDING/1"
STATIC_FORMAT = "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1"
SOURCE_FORMAT = "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1"


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _load_runtime_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "src" / "core" / "memory_pool_runtime.py"
    spec = importlib.util.spec_from_file_location("shift_memory_pool_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load memory runtime contract: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _semantic_roles(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence = contract.get("retail_source_semantic_evidence")
    if not isinstance(evidence, dict):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    allocation = evidence.get("allocation_size")
    if isinstance(allocation, dict) and allocation.get("proven") is True:
        helper = allocation.get("helper")
        index = allocation.get("source_argument_index")
        if isinstance(helper, str) and isinstance(index, int) and not isinstance(index, bool):
            rows[helper] = {
                "semantic_role": "allocation-size",
                "parameter_name": "allocation_size",
                "source_argument_index": index,
                "proven_callsite_count": allocation.get("proven_callsite_count"),
            }
    released = evidence.get("released_pointer")
    if isinstance(released, dict) and released.get("proven") is True:
        helper = released.get("helper")
        index = released.get("source_argument_index")
        if isinstance(helper, str) and isinstance(index, int) and not isinstance(index, bool):
            rows[helper] = {
                "semantic_role": "released-pointer",
                "parameter_name": "released_pointer",
                "source_argument_index": index,
                "proven_callsite_count": released.get("proven_callsite_count"),
            }
    return rows


def _wrapper_manifest(
    wrapper: dict[str, Any],
    role: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    name = str(wrapper.get("name") or "")
    storage = [str(value) for value in (wrapper.get("input_storage") or [])]
    forwarding_confirmed = wrapper.get("forwarding_confirmed") is True
    blockers: list[str] = []
    promoted_index: int | None = None
    if role is not None:
        candidate = role.get("source_argument_index")
        if not forwarding_confirmed:
            blockers.append("wrapper_forwarding_not_confirmed")
        elif not isinstance(candidate, int) or isinstance(candidate, bool):
            blockers.append("semantic_source_argument_index_invalid")
        elif candidate < 0 or candidate >= len(storage):
            blockers.append("semantic_source_argument_index_out_of_range")
        else:
            promoted_index = candidate

    parameters: list[dict[str, Any]] = []
    for index, entry_storage in enumerate(storage):
        semantic = role if promoted_index == index else None
        parameters.append(
            {
                "source_argument_index": index,
                "entry_storage": entry_storage,
                "name": semantic["parameter_name"] if semantic else f"arg{index}",
                "semantic_role": semantic["semantic_role"] if semantic else None,
                "semantic_role_proven": semantic is not None,
            }
        )

    semantic_count = sum(row["semantic_role_proven"] is True for row in parameters)
    status = "forwarding-unconfirmed"
    if forwarding_confirmed:
        status = "storage-shape-confirmed"
    if semantic_count:
        status = "partial-semantic-parameters"

    return (
        {
            "address": wrapper.get("address"),
            "name": name,
            "reported_calling_convention": wrapper.get("calling_convention"),
            "calling_convention_used_as_semantic_proof": False,
            "forwarding_confirmed": forwarding_confirmed,
            "input_storage": storage,
            "parameter_count": len(storage),
            "parameters": parameters,
            "semantic_parameter_count": semantic_count,
            "status": status,
            "blockers": blockers,
        },
        [f"{name}:{item}" for item in blockers],
    )


def build_memory_wrapper_runtime_manifest(
    forwarding_path: Path,
    static_summary_path: Path,
    source_summary_path: Path,
) -> dict[str, Any]:
    forwarding = _load(forwarding_path, FORWARDING_FORMAT)
    static_summary = _load(static_summary_path, STATIC_FORMAT)
    source_summary = _load(source_summary_path, SOURCE_FORMAT)

    runtime = _load_runtime_module()
    contract = runtime.build_memory_pool_contract(static_summary, source_summary)
    roles = _semantic_roles(contract)

    wrappers: list[dict[str, Any]] = []
    blockers: list[str] = []
    observed_names: set[str] = set()
    for raw in forwarding.get("wrappers") or []:
        if not isinstance(raw, dict):
            continue
        row, row_blockers = _wrapper_manifest(raw, roles.get(str(raw.get("name") or "")))
        wrappers.append(row)
        blockers.extend(row_blockers)
        observed_names.add(row["name"])

    for helper in sorted(roles):
        if helper not in observed_names:
            blockers.append(f"{helper}:wrapper_missing_from_forwarding")

    wrappers.sort(key=lambda row: (str(row.get("address") or ""), row["name"]))
    semantic_parameter_count = sum(int(row["semantic_parameter_count"]) for row in wrappers)
    helpers_with_semantics = [
        row["name"] for row in wrappers if int(row["semantic_parameter_count"]) > 0
    ]

    return {
        "format": FORMAT,
        "inputs": {
            "forwarding": str(forwarding_path),
            "static_summary": str(static_summary_path),
            "source_semantic_summary": str(source_summary_path),
        },
        "runtime_contract_status": contract.get("status"),
        "wrapper_count": len(wrappers),
        "forwarding_confirmed_wrapper_count": sum(
            row["forwarding_confirmed"] is True for row in wrappers
        ),
        "semantic_parameter_count": semantic_parameter_count,
        "helpers_with_proven_semantic_parameters": helpers_with_semantics,
        "wrappers": wrappers,
        "blockers": blockers,
        "scope": {
            "wrapper_function_identities_preserved": True,
            "entry_storage_preserved": True,
            "source_semantic_roles_gated_by_runtime_contract": True,
            "partial_parameter_semantics_proven": semantic_parameter_count > 0,
            "complete_helper_abi_proven": False,
            "calling_convention_semantics_proven": False,
            "pool_selector_role_proven": False,
            "alignment_role_proven": False,
            "release_flag_role_proven": False,
            "delete_kind_role_proven": False,
            "operator_new_identity_proven": False,
            "operator_delete_identity_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "Only source parameter roles admitted by the canonical memory runtime "
                "contract are named. Every other parameter remains argN even when its "
                "storage or value shape looks suggestive."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forwarding", type=Path, required=True)
    parser.add_argument("--static-summary", type=Path, required=True)
    parser.add_argument("--source-summary", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_memory_wrapper_runtime_manifest(
        args.forwarding,
        args.static_summary,
        args.source_summary,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"wrappers: {report['wrapper_count']}")
    print(f"confirmed forwarding: {report['forwarding_confirmed_wrapper_count']}")
    print(f"semantic parameters: {report['semantic_parameter_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

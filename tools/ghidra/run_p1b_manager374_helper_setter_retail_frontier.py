#!/usr/bin/env python3
"""Run and compose the bounded helper-mediated manager+0x374 setter probes."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "SHIFT.P1B.Manager374HelperSetterRetailFrontier/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

PROBES = {
    "direct_call_argument": {
        "path": ROOT / "tools/ghidra/analyze_p1b_manager374_materialized_direct_call_setters.py",
        "format": "SHIFT.P1B.Manager374MaterializedDirectCallSetterProbe/1",
        "candidate_count_key": "direct_callee_write_through_candidate_count",
        "candidate_rows_key": "direct_callee_write_through_candidates",
        "transport": "materialized-target-direct-helper-argument",
    },
    "helper_return_immediate": {
        "path": ROOT / "tools/ghidra/analyze_p1b_manager374_helper_returned_materialized_targets.py",
        "format": "SHIFT.P1B.Manager374HelperReturnedMaterializedTargetProbe/1",
        "candidate_count_key": "post_return_write_through_candidate_count",
        "candidate_rows_key": "post_return_write_through_candidates",
        "transport": "helper-returned-target-immediate-gpr",
    },
    "helper_return_stack": {
        "path": ROOT / "tools/ghidra/analyze_p1b_manager374_helper_return_stack_persistence.py",
        "format": "SHIFT.P1B.Manager374HelperReturnedTargetStackPersistenceProbe/1",
        "candidate_count_key": "stack_reload_derived_write_candidate_count",
        "candidate_rows_key": "stack_reload_derived_write_candidates",
        "transport": "helper-returned-target-stack-reload",
    },
}


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ValueError(f"cannot load probe: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_probes() -> dict[str, object]:
    modules: dict[str, object] = {}
    for name, cfg in PROBES.items():
        module = load_module(cfg["path"], f"p1b_helper_setter_{name}")
        require(getattr(module, "FORMAT", None) == cfg["format"], f"{name}: analyzer format drift")
        require(getattr(module, "RETAIL_SHA256", None) == RETAIL_SHA256, f"{name}: analyzer SHA lock drift")
        require(callable(getattr(module, "scan_rows", None)), f"{name}: scan_rows missing")
        modules[name] = module
    return modules


def validate_result(name: str, data: dict) -> None:
    cfg = PROBES[name]
    require(data.get("format") == cfg["format"], f"{name}: output format drift")
    require(data.get("ready") is True, f"{name}: output not ready")
    surface = data.get("surface")
    require(isinstance(surface, dict), f"{name}: missing surface")
    rows = surface.get(cfg["candidate_rows_key"])
    count = surface.get(cfg["candidate_count_key"])
    require(isinstance(rows, list), f"{name}: candidate rows missing")
    require(count == len(rows), f"{name}: candidate count mismatch")
    for row in rows:
        require(isinstance(row, dict), f"{name}: candidate row must be an object")
        require(isinstance(row.get("site"), str), f"{name}: candidate site missing")


def compose(results: dict[str, dict], *, decoded_instruction_count: int | None = None) -> dict:
    require(set(results) == set(PROBES), "probe bundle key drift")
    for name, data in results.items():
        validate_result(name, data)

    candidates: list[dict] = []
    per_probe_counts: dict[str, int] = {}
    for name, cfg in PROBES.items():
        rows = results[name]["surface"][cfg["candidate_rows_key"]]
        per_probe_counts[name] = len(rows)
        for row in rows:
            tagged = dict(row)
            tagged["source_probe"] = name
            tagged["transport_class"] = cfg["transport"]
            candidates.append(tagged)

    candidates.sort(
        key=lambda row: (
            str(row.get("site") or ""),
            str(row.get("callsite") or ""),
            str(row.get("source_probe") or ""),
        )
    )

    direct_surface = results["direct_call_argument"]["surface"]
    return_surface = results["helper_return_immediate"]["surface"]
    stack_surface = results["helper_return_stack"]["surface"]

    open_boundaries = {
        "materialized_target_indirect_call_argument_boundaries": int(
            direct_surface.get("indirect_call_argument_boundary_count", 0)
        ),
        "materialized_target_unresolved_direct_targets": int(
            direct_surface.get("unresolved_direct_target_count", 0)
        ),
        "helper_return_unresolved_direct_targets": int(
            return_surface.get("unresolved_direct_target_count", 0)
        ),
        "helper_return_non_stack_persistence_escapes": int(
            stack_surface.get("non_stack_persistence_escape_count", 0)
        ),
    }
    open_boundary_count = sum(open_boundaries.values())

    helper_counts = {
        "qualified_helper_return_target_count": int(
            return_surface.get("qualified_helper_return_target_count", 0)
        ),
        "qualified_helper_return_callsite_count": int(
            return_surface.get("qualified_helper_callsite_count", 0)
        ),
        "post_return_stack_scan_count": int(
            stack_surface.get("post_return_stack_scan_count", 0)
        ),
    }

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "single_shared_instruction_stream": True,
            "decoded_instruction_count": decoded_instruction_count,
        },
        "inputs": {name: cfg["format"] for name, cfg in PROBES.items()},
        "surface": {
            "probe_count": len(PROBES),
            "write_candidate_count_by_probe": per_probe_counts,
            "write_candidate_record_count": len(candidates),
            "write_candidate_records": candidates,
            "resolved_write_candidate_union_empty": len(candidates) == 0,
            "helper_return_counts": helper_counts,
            "open_boundary_count_by_class": open_boundaries,
            "open_boundary_count": open_boundary_count,
            "bounded_frontier_empty": len(candidates) == 0 and open_boundary_count == 0,
        },
        "adjudication": {
            "retail_helper_setter_probe_bundle_execution_complete": True,
            "retail_helper_setter_candidate_frontier_composed": True,
            "helper_setter_write_candidates_classified": False,
            "materialized_helper_mediated_setter_surface_complete": False,
            "helper_returned_materialized_address_surface_complete": False,
            "helper_returned_target_non_stack_persistence_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "external_or_unknown_origin_outer_alias_surface_complete": False,
            "independent_unnamed_opaque_or_external_runtime_root_synthesis_complete": False,
            "unrecognized_runtime_transform_root_origin_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This bundle composes only three bounded decoded-image helper-setter transports: materialized target passed to a direct helper, direct helper returning arg+0x374 with immediate GPR use, and stack spill/reload of that qualified returned target.",
            "A zero resolved candidate union does not close indirect helper calls, unresolved/external direct helpers, non-stack persistence of returned targets, unrelated opaque synthesis, generated code, or external process mutation.",
            "Open-boundary counts are acquisition frontiers, not proof that every boundary can produce a manager+0x374 write.",
            "No receiver or object identity is inferred from numeric +0x374 equality or from an ABI argument channel."
        ],
        "next_step": "Classify every positive write candidate and every nonzero open-boundary class from this single retail run. Close only empty or fully adjudicated bounded transports before considering the broader helper/non-vtable setter gate.",
    }


def run_rows(rows: list[tuple[int, str, str]]) -> tuple[dict, dict[str, dict]]:
    modules = load_probes()
    results = {name: module.scan_rows(rows) for name, module in modules.items()}
    return compose(results, decoded_instruction_count=len(rows)), results


def run(executable: Path) -> tuple[dict, dict[str, dict]]:
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected executable SHA: {digest}")
    modules = load_probes()
    return_module = modules["helper_return_immediate"]
    rows = return_module.disassemble(executable)
    results = {name: module.scan_rows(rows) for name, module in modules.items()}
    aggregate = compose(results, decoded_instruction_count=len(rows))
    return aggregate, results


def write_output(out_dir: Path, aggregate: dict, results: dict[str, dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "frontier.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, payload in results.items():
        enriched = dict(payload)
        enriched["authority"] = {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
        }
        (out_dir / f"{name}.json").write_text(json.dumps(enriched, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    aggregate, results = run(args.executable)
    if args.out_dir:
        write_output(args.out_dir, aggregate, results)
        print(args.out_dir / "frontier.json")
    else:
        print(json.dumps(aggregate, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

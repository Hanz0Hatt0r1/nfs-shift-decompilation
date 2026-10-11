#!/usr/bin/env python3
"""Run and compose the bounded materialized manager+0x374 retail probes.

This is an acquisition/composition tool. It does not classify receiver identity and
therefore does not promote the final manager+0x374 -> HDVehicle+0x4330 join.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.Manager374MaterializedRetailFrontier/1"

PROBES = {
    "same_region": {
        "path": ROOT / "tools/ghidra/analyze_p1b_manager374_materialized_plus374_writers.py",
        "format": "SHIFT.P1B.Manager374MaterializedPlus374WriterProbe/1",
        "candidate_count_key": "zero_displacement_write_candidate_count",
        "candidate_rows_key": "zero_displacement_write_candidates",
        "transport": "same-region-gpr",
    },
    "ebp_spill_reload": {
        "path": ROOT / "tools/ghidra/analyze_p1b_manager374_materialized_ebp_spill_reload.py",
        "format": "SHIFT.P1B.Manager374MaterializedEbpSpillReloadProbe/1",
        "candidate_count_key": "reload_derived_zero_displacement_write_candidate_count",
        "candidate_rows_key": "reload_derived_zero_displacement_write_candidates",
        "transport": "ebp-spill-reload",
    },
    "esp_spill_reload": {
        "path": ROOT / "tools/ghidra/analyze_p1b_manager374_materialized_esp_spill_reload.py",
        "format": "SHIFT.P1B.Manager374MaterializedESPSpillReloadProbe/1",
        "candidate_count_key": "reload_derived_zero_displacement_write_candidate_count",
        "candidate_rows_key": "reload_derived_zero_displacement_write_candidates",
        "transport": "esp-normalized-spill-reload",
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


def validate_probe(name: str, data: dict) -> None:
    cfg = PROBES[name]
    require(data.get("format") == cfg["format"], f"{name}: format drift")
    require(data.get("ready") is True, f"{name}: probe not ready")
    authority = data.get("authority")
    require(isinstance(authority, dict), f"{name}: missing retail authority")
    require(
        authority.get("retail_executable_sha256") == RETAIL_SHA256,
        f"{name}: retail hash drift",
    )
    surface = data.get("surface")
    require(isinstance(surface, dict), f"{name}: missing surface")
    rows = surface.get(cfg["candidate_rows_key"])
    count = surface.get(cfg["candidate_count_key"])
    require(isinstance(rows, list), f"{name}: candidate rows missing")
    require(count == len(rows), f"{name}: candidate count mismatch")
    for row in rows:
        require(isinstance(row, dict), f"{name}: candidate row is not an object")
        require(isinstance(row.get("site"), str), f"{name}: candidate site missing")
        require(isinstance(row.get("receiver_register"), str), f"{name}: receiver provenance missing")
        require(isinstance(row.get("materializer_site"), str), f"{name}: materializer provenance missing")


def compose(results: dict[str, dict]) -> dict:
    require(set(results) == set(PROBES), "probe bundle key drift")
    for name, data in results.items():
        validate_probe(name, data)

    records: list[dict] = []
    site_sources: dict[str, set[str]] = {}
    per_probe_counts: dict[str, int] = {}

    for name, cfg in PROBES.items():
        rows = results[name]["surface"][cfg["candidate_rows_key"]]
        per_probe_counts[name] = len(rows)
        for row in rows:
            tagged = dict(row)
            tagged["source_probe"] = name
            tagged["transport_class"] = cfg["transport"]
            records.append(tagged)
            site_sources.setdefault(row["site"], set()).add(name)

    records.sort(key=lambda row: (row["site"], row["source_probe"], row.get("materializer_site", "")))
    unique_sites = sorted(site_sources)
    source_rows = [
        {"site": site, "source_probes": sorted(site_sources[site])}
        for site in unique_sites
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "all_probe_outputs_same_authoritative_executable": True,
        },
        "inputs": {name: cfg["format"] for name, cfg in PROBES.items()},
        "surface": {
            "probe_count": len(PROBES),
            "candidate_record_count_by_probe": per_probe_counts,
            "candidate_record_count": len(records),
            "candidate_records": records,
            "unique_candidate_site_count": len(unique_sites),
            "unique_candidate_sites": unique_sites,
            "candidate_site_sources": source_rows,
            "unadjudicated_candidate_site_count": len(unique_sites),
            "unadjudicated_candidate_sites": unique_sites,
        },
        "adjudication": {
            "retail_materialized_probe_bundle_execution_complete": True,
            "retail_materialized_candidate_frontier_composed": True,
            "all_materialized_candidate_receivers_classified": False,
            "computed_address_manager_374_writer_surface_complete": False,
            "unknown_or_unrelated_manager_root_alias_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes only the three already-bounded materialized receiver+0x374 transport classes: same-region GPR, EBP spill/reload and normalized ESP spill/reload.",
            "A positive row proves syntactic receiver-register provenance to a materialized +0x374 address, not Participants Manager identity.",
            "Indexed/arithmetic address construction, cross-control-flow carry, non-stack memory aliases, helper-returned addresses, runtime mutation and arbitrary process memory remain outside this bundle.",
            "A zero candidate union would close only these three bounded transport classes; it would not by itself close helper/runtime/global manager-root surfaces.",
        ],
        "next_step": "Machine-adjudicate every unique positive candidate receiver against Participants Manager identity; extend only concrete surviving transport classes before the final manager+0x374 -> HDVehicle+0x4330 join and slot2 adjudication.",
    }


def run(executable: Path) -> dict:
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected executable SHA: {digest}")

    results: dict[str, dict] = {}
    for name, cfg in PROBES.items():
        module = load_module(cfg["path"], f"p1b_materialized_{name}")
        module_sha = getattr(module, "RETAIL_SHA256", None)
        module_format = getattr(module, "FORMAT", None)
        require(module_sha == RETAIL_SHA256, f"{name}: analyzer SHA lock drift")
        require(module_format == cfg["format"], f"{name}: analyzer format drift")
        results[name] = module.analyze(executable)
    return compose(results)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.executable)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Compose the bounded P1B runtime-callback/indirect-entry coverage already proven on retail 1.02."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/1"
EXPECTED = {
    "thread": "SHIFT.P1B.HDVehicle4330ThreadStartCallbackSurface/1",
    "nonthread": "SHIFT.P1B.HDVehicle4330NonThreadCallbackClosure/1",
    "massive": "SHIFT.P1B.HDVehicle4330MassiveThreadCallbackWrapper/1",
    "qsort": "SHIFT.P1B.HDVehicle4330QsortCallbackSurface/1",
    "winmm": "SHIFT.P1B.HDVehicle4330WinMMCallbackSurface/1",
}
EXPECTED_PROVIDER_COUNT = 7
EXPECTED_TOTAL_CALLSITES = 45
EXPECTED_UNIQUE_ENTRYPOINTS = 33


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def addr(value: str) -> str:
    value = value.lower()
    if not value.startswith("0x"):
        raise ValueError(f"not an address: {value!r}")
    return value


def build(thread_path: Path, nonthread_path: Path, massive_path: Path, qsort_path: Path, winmm_path: Path) -> dict:
    data = {
        "thread": load(thread_path),
        "nonthread": load(nonthread_path),
        "massive": load(massive_path),
        "qsort": load(qsort_path),
        "winmm": load(winmm_path),
    }
    for name, doc in data.items():
        if doc.get("format") != EXPECTED[name]:
            raise ValueError(f"{name} format mismatch: {doc.get('format')!r}")
        if doc.get("ready") is not True:
            raise ValueError(f"{name} evidence is not ready")
        if doc.get("adjudication", {}).get("external_provider_count") != EXPECTED_PROVIDER_COUNT:
            raise ValueError(f"{name} provider-count drift")

    thread = data["thread"]
    nonthread = data["nonthread"]
    massive = data["massive"]
    qsort = data["qsort"]
    winmm = data["winmm"]

    if thread["surface"]["exact_4330_carrier_thread_start_count"] != 0 or thread["adjudication"]["exact_4330_carrier_thread_start_found"] is not False:
        raise ValueError("thread-start carrier intersection drift")
    if nonthread["surface"]["exact_4330_carrier_callback_count"] != 0 or nonthread["adjudication"]["exact_4330_carrier_registered_as_selected_nonthread_callback"] is not False:
        raise ValueError("selected non-thread carrier intersection drift")
    if massive["surface"]["exact_4330_carrier_callback_count"] != 0 or massive["adjudication"]["exact_4330_carrier_reachable_via_massive_thread_wrapper"] is not False:
        raise ValueError("Massive wrapper carrier intersection drift")
    if qsort["surface"]["exact_4330_carrier_comparator_count"] != 0 or qsort["adjudication"]["exact_4330_carrier_reachable_via_qsort"] is not False:
        raise ValueError("qsort carrier intersection drift")
    if winmm["surface"]["exact_4330_carrier_callback_count"] != 0 or winmm["adjudication"]["exact_4330_carrier_reachable_via_winmm"] is not False:
        raise ValueError("WinMM carrier intersection drift")

    if thread["adjudication"]["runtime_thread_start_callback_subset_complete"] is not True:
        raise ValueError("thread-start subset reopened")
    if nonthread["adjudication"]["selected_nonthread_callback_frontier_complete"] is not True:
        raise ValueError("selected non-thread frontier reopened")
    if massive["adjudication"]["massive_thread_callback_wrapper_surface_complete"] is not True:
        raise ValueError("Massive wrapper reopened")
    if qsort["adjudication"]["qsort_callback_surface_complete"] is not True:
        raise ValueError("qsort surface reopened")
    if winmm["adjudication"]["winmm_callback_surface_complete"] is not True:
        raise ValueError("WinMM surface reopened")

    entrypoints: set[str] = set()
    for row in thread["surface"]["resolved_thread_starts"]:
        entrypoints.add(addr(row["address"]))
    for row in nonthread["surface"]["nonnull_callbacks"]:
        entrypoints.add(addr(row["callback"]))
    for row in massive["surface"]["resolved_callbacks"]:
        entrypoints.add(addr(row["address"]))
    for row in qsort["surface"]["possible_comparator_entrypoints"]:
        entrypoints.add(addr(row["address"]))
    for row in winmm["surface"]["nonnull_callbacks"]:
        entrypoints.add(addr(row["address"]))

    coverage = [
        {
            "surface": "CreateThread/__beginthreadex",
            "physical_callsite_count": thread["surface"]["create_thread_direct_callsite_count"] + thread["surface"]["beginthreadex_direct_callsite_count"],
            "possible_entrypoint_count": thread["surface"]["resolved_thread_start_count"],
            "exact_4330_carrier_hit_count": 0,
        },
        {
            "surface": "selected Win32/Winsock non-thread callbacks",
            "physical_callsite_count": nonthread["surface"]["frontier_callsite_count"],
            "possible_entrypoint_count": nonthread["surface"]["distinct_nonnull_callback_count"],
            "exact_4330_carrier_hit_count": 0,
        },
        {
            "surface": "FUN_0061cdf0 Massive callback wrapper",
            "physical_callsite_count": massive["surface"]["direct_caller_count"],
            "possible_entrypoint_count": massive["surface"]["resolved_callback_count"],
            "exact_4330_carrier_hit_count": 0,
        },
        {
            "surface": "CRT _qsort comparators",
            "physical_callsite_count": qsort["surface"]["direct_qsort_callsite_count"],
            "possible_entrypoint_count": qsort["surface"]["possible_comparator_entrypoint_count"],
            "exact_4330_carrier_hit_count": 0,
        },
        {
            "surface": "WinMM waveOut/waveIn/timeSetEvent callbacks",
            "physical_callsite_count": winmm["surface"]["physical_callsite_count"],
            "possible_entrypoint_count": winmm["surface"]["nonnull_callback_entrypoint_count"],
            "exact_4330_carrier_hit_count": 0,
        },
    ]
    total_callsites = sum(row["physical_callsite_count"] for row in coverage)
    if total_callsites != EXPECTED_TOTAL_CALLSITES:
        raise ValueError(f"bounded callback callsite count drift: {total_callsites}")
    if len(entrypoints) != EXPECTED_UNIQUE_ENTRYPOINTS:
        raise ValueError(f"unique callback entrypoint count drift: {len(entrypoints)}")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [EXPECTED[k] for k in ("thread", "nonthread", "massive", "qsort", "winmm")],
        "surface": {
            "closed_surface_count": len(coverage),
            "bounded_callback_capable_callsite_count": total_callsites,
            "unique_possible_callback_entrypoint_count": len(entrypoints),
            "exact_4330_carrier_entrypoint_hit_count": 0,
            "coverage": coverage,
            "possible_entrypoints": sorted(entrypoints),
        },
        "adjudication": {
            "bounded_runtime_callback_coverage_composed": True,
            "bounded_runtime_callback_exact_4330_carrier_hit_found": False,
            "runtime_callback_registration_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "remaining_callback_api_families_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This composes only five callback/indirect-entry surfaces already proven by dedicated retail contracts.",
            "It does not claim that all callback-capable APIs or application-owned wrappers are inventoried.",
            "Generic function-pointer stores/copies, computed or encoded code pointers, vtable-driven runtime registration and other indirect dispatch remain open."
        ],
        "next_step": "Use this aggregate as the no-duplication baseline, then inventory remaining finite callback API families and generic function-pointer stores/copies before promoting global indirect-entry gates."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("thread", type=Path)
    p.add_argument("nonthread", type=Path)
    p.add_argument("massive", type=Path)
    p.add_argument("qsort", type=Path)
    p.add_argument("winmm", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = build(args.thread, args.nonthread, args.massive, args.qsort, args.winmm)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        p.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compose the complete P1B selected non-thread callback-registration closure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330NonThreadCallbackClosure/1"
T1_FORMAT = "SHIFT.P1B.HDVehicle4330NonThreadCallbackTranche1/1"
T2_FORMAT = "SHIFT.P1B.HDVehicle4330NonThreadCallbackTranche2/1"
WINSOCK_FORMAT = "SHIFT.Process1TimerWinsockApcSurface/1"

EXPECTED_NON_NULL = {
    "0x00634b89": "0x00634870",
    "0x00634c52": "0x00634870",
    "0x00634c93": "0x00634870",
    "0x006558d5": "0x006553e0",
    "0x00655c15": "0x006553e0",
    "0x006559df": "0x00655410",
    "0x00655dca": "0x00655410",
}
EXPECTED_NULL = {
    "0x0099882b": "SetWaitableTimer",
    "0x00998e13": "SetWaitableTimer",
    "0x005fdd21": "WSARecv",
    "0x005fdd09": "WSARecvFrom",
}
CANONICAL_P1B_CARRIERS = {
    "0x00769520", "0x0076b130", "0x0076df50", "0x00768a4d", "0x00756050",
    "0x00772200", "0x00772570", "0x007c3b00", "0x0076b280", "0x007618f0",
    "0x00769640", "0x007567a0", "0x00756bb0", "0x00771db0", "0x00771e10",
}


def load(path: Path, expected_format: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != expected_format or data.get("ready") is not True:
        raise ValueError(f"unexpected evidence contract: {path}")
    return data


def build(tranche1: Path, tranche2: Path, timer_winsock: Path) -> dict:
    t1 = load(tranche1, T1_FORMAT)
    t2 = load(tranche2, T2_FORMAT)
    tw = load(timer_winsock, WINSOCK_FORMAT)

    resolved_non_null: dict[str, str] = {}
    for row in t1["surface"]["resolved_callbacks"]:
        callback = str(row["address"]).lower()
        for callsite in row["callsites"]:
            resolved_non_null[str(callsite).lower()] = callback
    if resolved_non_null != EXPECTED_NON_NULL:
        raise ValueError(f"tranche1 callback surface drift: {resolved_non_null!r}")

    resolved_null = {
        str(row["callsite"]).lower(): str(row["api"])
        for row in t2["surface"]["resolved_sites"]
        if row.get("callback") == "NULL"
    }
    wsa = tw["winsock_completion_surface"]["wsarecvfrom_machine_abi"]
    if str(wsa.get("callsite")).lower() != "0x005fdd09":
        raise ValueError("WSARecvFrom callsite drift")
    if "NULL" not in str(wsa["arguments"][8].get("value")):
        raise ValueError("WSARecvFrom completion routine is no longer proven NULL")
    if wsa.get("exact_hdvehicle_4330_carrier_reachable_via_completion_routine") is not False:
        raise ValueError("WSARecvFrom exact-carrier negative drift")
    resolved_null["0x005fdd09"] = "WSARecvFrom"
    if resolved_null != EXPECTED_NULL:
        raise ValueError(f"null callback surface drift: {resolved_null!r}")

    nonnull_callbacks = set(resolved_non_null.values())
    exact_hits = sorted(nonnull_callbacks & CANONICAL_P1B_CARRIERS)
    if exact_hits:
        raise ValueError(f"exact P1B carrier registered as callback: {exact_hits!r}")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "frontier_callsite_count": 11,
            "resolved_callsite_count": 11,
            "remaining_callsite_count": 0,
            "nonnull_callback_callsite_count": len(resolved_non_null),
            "null_callback_callsite_count": len(resolved_null),
            "distinct_nonnull_callback_count": len(nonnull_callbacks),
            "exact_4330_carrier_callback_count": 0,
            "nonnull_callbacks": [
                {"callsite": callsite, "callback": callback}
                for callsite, callback in sorted(resolved_non_null.items())
            ],
            "null_callbacks": [
                {"callsite": callsite, "api": api}
                for callsite, api in sorted(resolved_null.items())
            ],
        },
        "adjudication": {
            "selected_nonthread_callback_argument_provenance_complete": True,
            "selected_nonthread_callback_frontier_complete": True,
            "exact_4330_carrier_registered_as_selected_nonthread_callback": False,
            "runtime_callback_registration_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes only the selected Win32/Winsock non-thread callback families originally pinned by the P1B frontier.",
            "Other callback-registration families, generic function-pointer stores/copies, computed/encoded pointers and unresolved indirect dispatch remain outside this closure.",
            "Closing this selected callback frontier does not promote the global runtime-callback or indirect-entry gates.",
        ],
        "next_step": "Continue generic runtime function-pointer stores/copies and remaining indirect-entry mechanisms before attempting the manager+0x374 identity join.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("tranche1", type=Path)
    p.add_argument("tranche2", type=Path)
    p.add_argument("timer_winsock", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = build(args.tranche1, args.tranche2, args.timer_winsock)
    except ValueError as exc:
        p.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

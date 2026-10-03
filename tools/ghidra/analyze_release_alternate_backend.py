#!/usr/bin/env python3
"""Join the proven release-pointer wrapper input to FUN_0064f260.

The ordinary release-pointer chain proves a wrapper entry storage by tracing the
retail pool-free `%p` diagnostic backwards through FUN_0064f3a0 and the
0x0064f4c0 thunk.  FUN_00886950 also has an alternate branch to FUN_0064f260.
This analyzer asks one deliberately narrow question: does that alternate branch
forward the *same already-proven wrapper input* to one physical backend entry
storage?

A positive result assigns only the physical `released-pointer` role to that
FUN_0064f260 entry storage.  It does not assign semantics to any other backend
input or prove what FUN_0064f260 does with the pointer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT-MEMORY-RELEASE-ALTERNATE-BACKEND/1"
RELEASE_CHAIN_FORMAT = "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1"
FORWARDING_FORMAT = "SHIFT-MEMORY-WRAPPER-FORWARDING/1"

WRAPPER = "FUN_00886950"
WRAPPER_ADDRESS = "0x00886950"
ALTERNATE_BACKEND = "0x0064f260"


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _norm_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("thunk_fun_"):
        token = token[10:]
    elif token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError:
        return None


def _proven_wrapper_storage(release_chain: dict[str, Any]) -> tuple[str | None, list[str]]:
    storages = sorted(
        {
            str(row.get("wrapper_input_storage"))
            for row in (release_chain.get("wrapper_paths") or [])
            if isinstance(row, dict)
            and row.get("wrapper") == WRAPPER
            and row.get("released_pointer_path_proven") is True
            and isinstance(row.get("wrapper_input_storage"), str)
            and row.get("wrapper_input_storage")
        }
    )
    if release_chain.get("release_pointer_to_wrapper_storage_proven") is not True:
        return None, ["release_pointer_chain_not_proven"]
    if not storages:
        return None, ["wrapper_released_pointer_storage_not_proven"]
    if len(storages) != 1:
        return None, ["wrapper_released_pointer_storage_conflict"]
    return storages[0], []


def _alternate_sites(
    forwarding: dict[str, Any],
    wrapper_storage: str | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    wrapper = next(
        (
            row
            for row in (forwarding.get("wrappers") or [])
            if isinstance(row, dict)
            and (
                row.get("name") == WRAPPER
                or _norm_address(row.get("address")) == WRAPPER_ADDRESS
            )
        ),
        None,
    )
    if not isinstance(wrapper, dict):
        return [], ["alternate_wrapper_not_found"]
    if wrapper.get("forwarding_confirmed") is not True:
        return [], ["alternate_wrapper_forwarding_not_confirmed"]

    expected_source = f"input:{wrapper_storage}" if wrapper_storage else None
    sites: list[dict[str, Any]] = []
    for site in wrapper.get("call_sites") or []:
        if not isinstance(site, dict) or _norm_address(site.get("target")) != ALTERNATE_BACKEND:
            continue
        arguments = [arg for arg in (site.get("arguments") or []) if isinstance(arg, dict)]
        matches = [
            arg
            for arg in arguments
            if expected_source is not None
            and arg.get("resolved") is True
            and arg.get("source") == expected_source
            and isinstance(arg.get("storage"), str)
            and arg.get("storage")
        ]
        sites.append(
            {
                "instruction": _norm_address(site.get("instruction")),
                "transfer_kind": site.get("transfer_kind"),
                "target": ALTERNATE_BACKEND,
                "wrapper_released_pointer_storage": wrapper_storage,
                "matching_argument_count": len(matches),
                "released_pointer_backend_storage": (
                    str(matches[0]["storage"]) if len(matches) == 1 else None
                ),
                "arguments": [
                    {
                        "storage": arg.get("storage"),
                        "source": arg.get("source"),
                        "resolved": arg.get("resolved") is True,
                        "same_as_proven_released_pointer": arg in matches,
                    }
                    for arg in arguments
                ],
                "site_proven": len(matches) == 1,
            }
        )

    if not sites:
        return [], ["alternate_backend_transfer_not_found"]
    if any(site["site_proven"] is not True for site in sites):
        return sites, ["alternate_backend_pointer_match_not_unique"]
    return sites, []


def analyze_release_alternate_backend(
    release_chain_path: Path,
    forwarding_path: Path,
) -> dict[str, Any]:
    release_chain = _load(release_chain_path, RELEASE_CHAIN_FORMAT)
    forwarding = _load(forwarding_path, FORWARDING_FORMAT)

    wrapper_storage, storage_blockers = _proven_wrapper_storage(release_chain)
    sites, site_blockers = _alternate_sites(forwarding, wrapper_storage)
    storages = sorted(
        {
            str(site["released_pointer_backend_storage"])
            for site in sites
            if site.get("site_proven") is True
            and site.get("released_pointer_backend_storage")
        }
    )

    blockers = list(storage_blockers) + list(site_blockers)
    if sites and not site_blockers and len(storages) != 1:
        blockers.append("alternate_backend_pointer_storage_conflict")

    proven = not blockers and len(storages) == 1
    backend_storage = storages[0] if proven else None

    all_backend_storages = sorted(
        {
            str(arg.get("storage"))
            for site in sites
            for arg in (site.get("arguments") or [])
            if isinstance(arg, dict) and isinstance(arg.get("storage"), str)
        }
    )
    unresolved_semantic_storages = [
        storage for storage in all_backend_storages if storage != backend_storage
    ]

    return {
        "format": FORMAT,
        "release_pointer_chain": str(release_chain_path),
        "wrapper_forwarding": str(forwarding_path),
        "wrapper": WRAPPER,
        "wrapper_address": WRAPPER_ADDRESS,
        "alternate_backend": ALTERNATE_BACKEND,
        "proven_released_pointer_wrapper_storage": wrapper_storage,
        "alternate_site_count": len(sites),
        "alternate_sites": sites,
        "alternate_backend_released_pointer_entry_storage": backend_storage,
        "released_pointer_to_alternate_backend_storage_proven": proven,
        "other_alternate_backend_entry_storage": unresolved_semantic_storages,
        "blockers": blockers,
        "scope": {
            "diagnostic_proven_wrapper_pointer_reused": wrapper_storage is not None,
            "wrapper_forwarding_used": True,
            "alternate_backend_released_pointer_role_proven": proven,
            "alternate_backend_function_semantics_proven": False,
            "other_alternate_backend_argument_roles_proven": False,
            "release_flag_role_proven": False,
            "delete_kind_role_proven": False,
            "pool_selector_role_proven": False,
            "operator_delete_identity_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "A positive result proves only that the same wrapper entry value already "
                "identified as the retail released pointer on the diagnostic-backed path "
                "is forwarded into one physical FUN_0064f260 entry storage. It does not "
                "assign semantics to FUN_0064f260 itself or to its other inputs."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_chain", type=Path)
    parser.add_argument("--forwarding", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_release_alternate_backend(args.release_chain, args.forwarding)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"alternate sites: {report['alternate_site_count']}")
    print(
        "alternate backend released-pointer storage: "
        f"{report['alternate_backend_released_pointer_entry_storage']}"
    )
    print(
        "released pointer to alternate backend proven: "
        f"{report['released_pointer_to_alternate_backend_storage_proven']}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

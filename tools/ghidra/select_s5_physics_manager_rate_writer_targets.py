#!/usr/bin/env python3
"""Select a bounded retail function window for cPhysicsManager +0x388 writer discovery.

The address window is deliberately a discovery boundary only.  It contains the
source-backed Physics Manager constructor/accessor chain and the known scheduler
consumer, but address proximity is never promoted to class membership.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.PhysicsManagerRateWriterTargetSelection/1"
WINDOW_START = 0x0070F000
WINDOW_END = 0x00713050

ANCHORS = {
    0x0070FAE0: {
        "name": "FUN_0070fae0",
        "mnemonic_sha256": "072f0f9df5e4b00b2ff7cdbf991923afacaa82bcdac508310f3eb0a3e5941859",
        "role": "source-backed Physics Manager constructor",
    },
    0x0070FE90: {
        "name": "FUN_0070fe90",
        "mnemonic_sha256": "a81f2450cab727e62d5915024328163bbc4ba11d7c1d57322e48dead4ff422d1",
        "role": "scheduler rate accessor",
    },
    0x00713050: {
        "name": "FUN_00713050",
        "mnemonic_sha256": "94632f5b4eeda1f8741fff25238ab30068a48a27cddfdcef7b47757ee6c93195",
        "role": "source-visible +0x388 scheduler consumer",
    },
}


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


def _hex(value: int) -> str:
    return f"0x{value:08x}"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(value)
    return rows


def select(functions_path: Path) -> dict[str, Any]:
    rows = _read_jsonl(functions_path)
    by_address: dict[int, dict[str, Any]] = {}
    for row in rows:
        address = _norm(row.get("address"))
        if address is not None:
            by_address[address] = row

    anchor_rows: list[dict[str, Any]] = []
    for address, expected in ANCHORS.items():
        row = by_address.get(address)
        if row is None:
            raise ValueError(f"missing required anchor {_hex(address)}")
        if row.get("name") != expected["name"]:
            raise ValueError(f"{_hex(address)} anchor name drift")
        if row.get("mnemonic_sha256") != expected["mnemonic_sha256"]:
            raise ValueError(f"{_hex(address)} anchor fingerprint drift")
        anchor_rows.append(
            {
                "address": _hex(address),
                "name": expected["name"],
                "role": expected["role"],
                "fingerprint_verified": True,
            }
        )

    selected: list[dict[str, Any]] = []
    for address, row in sorted(by_address.items()):
        if not (WINDOW_START <= address <= WINDOW_END):
            continue
        if row.get("external") is True:
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{_hex(address)}: selected internal function has no name")
        selected.append(
            {
                "address": _hex(address),
                "name": name,
                "calling_convention": row.get("calling_convention"),
                "size": row.get("size"),
                "thunk": bool(row.get("thunk")),
                "mnemonic_sha256": row.get("mnemonic_sha256"),
                "class_membership_proven": False,
                "selected_by": "bounded-address-window-only",
            }
        )

    selected_addresses = {row["address"] for row in selected}
    missing_anchors = [row for row in anchor_rows if row["address"] not in selected_addresses]
    if missing_anchors:
        raise ValueError(f"required anchor fell outside selected window: {missing_anchors}")
    if not selected:
        raise ValueError("bounded Physics Manager discovery window selected no functions")

    return {
        "format": FORMAT,
        "status": "bounded-discovery-targets-ready",
        "functions_input": str(functions_path),
        "window": {
            "start": _hex(WINDOW_START),
            "end": _hex(WINDOW_END),
            "inclusive": True,
            "selection_semantics": "candidate-discovery-only",
        },
        "anchors": anchor_rows,
        "target_count": len(selected),
        "targets": selected,
        "target_names": [row["name"] for row in selected],
        "scope": {
            "address_adjacency_proves_class_membership": False,
            "selected_function_is_cPhysicsManager_method": False,
            "selected_function_writes_plus_0x388": False,
            "field_semantics_proven": False,
            "physical_units_proven": False,
            "retail_cadence_admitted": False,
            "purpose": "bound the instruction-export cost before syntactic +0x388 writer discovery",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("functions_jsonl", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--names-out", type=Path)
    args = parser.parse_args()

    report = select(args.functions_jsonl)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.names_out:
        args.names_out.parent.mkdir(parents=True, exist_ok=True)
        args.names_out.write_text("\n".join(report["target_names"]) + "\n", encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"targets: {report['target_count']}")
    print(f"window: {report['window']['start']}..{report['window']['end']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.names_out:
        print(f"names: {args.names_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

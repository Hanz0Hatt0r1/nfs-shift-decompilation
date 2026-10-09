#!/usr/bin/env python3
"""Compose machine-proven selected-wheel paths with source-visible storage syntax.

This closes only derived wheel aliases already identified by merged P1D machine
contracts. The pinned decompiler source is a navigation/cross-check artifact;
selected-object identity remains owned by the upstream machine contracts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3DerivedWheelStorageHandoff/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
DIRECT_FORMAT = "SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1"
CHILD_FORMAT = "SHIFT.P1D.Slot3Fun00755f80WheelChildClosure/1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path, fmt: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != fmt or payload.get("ready") is not True:
        raise ValueError(f"{path}: unexpected or unready contract")
    return payload


def extract(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise ValueError(f"missing function signature: {signature}")
    tail = text[start + len(signature):]
    match = re.search(
        r"\n\n(?:void|float10|undefined\d*|int|uint|double|char|long|short|bool|byte|word|dword|ulong|longlong)\s+(?:__\w+\s+)?FUN_[0-9a-fA-F]+\(",
        tail,
    )
    end = len(text) if match is None else start + len(signature) + match.start()
    return text[start:end]


def build(source: Path, direct_path: Path, child_path: Path) -> dict:
    digest = sha256(source)
    if digest != SOURCE_SHA256:
        raise ValueError(f"unexpected SHIFT.exe.c SHA-256: {digest}")
    direct = load(direct_path, DIRECT_FORMAT)
    child = load(child_path, CHILD_FORMAT)

    if direct.get("selected_slot3", {}).get("hdvehicle_offset") != "0x2380":
        raise ValueError("selected slot3 offset drift")
    d60 = direct.get("paths", {}).get("fun00760b50", {})
    if d60.get("receiver") != "HDVehicle+0x2380" or d60.get("target_overlap") is not False:
        raise ValueError("FUN_00760b50 exact selected-wheel proof drift")
    caller = child.get("caller", {})
    if (
        caller.get("function") != "FUN_00763570"
        or caller.get("wheel_seed") != "HDVehicle+0x400"
        or caller.get("stride") != "0xa80"
        or caller.get("iteration_count") != 4
        or caller.get("slot3_receiver") != "HDVehicle+0x2380"
    ):
        raise ValueError("FUN_00763570 four-wheel machine proof drift")
    if child.get("callee", {}).get("fun00755f80_exact_wheel_escape_found") is True:
        raise ValueError("upstream FUN_00755f80 escape status drift")

    text = source.read_text(encoding="utf-8", errors="replace")
    f63570 = extract(text, "void __thiscall FUN_00763570(void *this,double param_1)")
    f70e80 = extract(text, "void __thiscall FUN_00770e80(void *this,undefined8 param_1,undefined8 param_2,char param_3)")

    iterator_lines = [line.strip() for line in f63570.splitlines() if "local_18._4_4_" in line]
    expected_prefix = [
        "local_18._4_4_ = (float)((int)this + 0x400);",
        "fVar8 = FUN_00755f80((int)local_18._4_4_);",
        "local_18._4_4_ = (float)((int)local_18._4_4_ + 0xa80);",
    ]
    if iterator_lines[:3] != expected_prefix:
        raise ValueError(f"FUN_00763570 wheel iterator surface drift: {iterator_lines!r}")
    # The next use after the loop must overwrite the same decompiler storage before
    # it is reused as an unrelated float temporary. This prevents treating later
    # float uses as wheel-pointer escapes.
    if len(iterator_lines) < 4 or iterator_lines[3] != "local_18._4_4_ = (float)local_40;":
        raise ValueError("FUN_00763570 iterator storage is not overwritten after wheel loop")

    selected_lines = [line.strip() for line in f70e80.splitlines() if "0x2380" in line]
    if selected_lines != [
        "FUN_00760b50((void *)((int)this + 0x2380),*(double *)((int)this + 0xa0),iVar2);"
    ]:
        raise ValueError(f"FUN_00770e80 selected-wheel source surface drift: {selected_lines!r}")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [DIRECT_FORMAT, CHILD_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_decompiler_source_sha256": digest,
            "machine_contracts_adjudicate_selected_wheel_identity": True,
            "source_is_storage_navigation_crosscheck": True,
        },
        "selected_slot3": {
            "wheel_receiver": "HDVehicle+0x2380",
            "local_target": "+0x538",
            "absolute_target": "HDVehicle+0x28b8..+0x28bf",
        },
        "derived_aliases": {
            "FUN_00763570": {
                "storage": "stack/local decompiler temporary local_18._4_4_",
                "machine_proven_seed": "HDVehicle+0x400",
                "machine_proven_stride": "0xa80",
                "machine_proven_iteration_count": 4,
                "source_seed": "local_18._4_4_ = this+0x400",
                "source_consumer": "FUN_00755f80(local_18._4_4_)",
                "source_advance": "local_18._4_4_ += 0xa80",
                "storage_overwritten_after_wheel_loop": True,
                "persistent_store_of_derived_wheel_pointer_found": False,
                "forward_beyond_already_closed_FUN_00755f80_found": False,
            },
            "FUN_00770e80": {
                "machine_proven_selected_receiver": "HDVehicle+0x2380",
                "source_materialization": "inline this+0x2380 call argument",
                "source_consumer": "FUN_00760b50",
                "source_selected_materialization_count": 1,
                "persistent_store_of_selected_wheel_pointer_found": False,
                "forward_beyond_already_closed_FUN_00760b50_found": False,
            },
        },
        "adjudication": {
            "source_visible_machine_proven_derived_wheel_storage_subset_complete": True,
            "source_visible_machine_proven_derived_wheel_persistent_store_found": False,
            "source_visible_machine_proven_derived_wheel_new_forward_found": False,
            "other_derived_alias_storage_ruled_out": False,
            "machine_register_alias_storage_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes only the two source-visible derived-wheel materializations already proven semantically by merged machine contracts.",
            "The decompiler's float type for local_18._4_4_ is not treated as semantic pointer typing; exact wheel identity comes from the upstream machine transfer proof.",
            "Other register-only, callee-created, aggregate, stored, or callback-carried aliases remain open.",
        ],
        "next_step": "Inventory machine register aliases and callee-created selected-wheel aliases outside these two already-closed source-visible paths; require exact selected-root provenance before testing persistence or callbacks.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("direct_carrier", type=Path)
    parser.add_argument("wheel_child", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = build(args.source, args.direct_carrier, args.wheel_child)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

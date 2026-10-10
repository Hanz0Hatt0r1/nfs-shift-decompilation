#!/usr/bin/env python3
"""Compose the bounded P1.3A exact-wheel-root materializer/derived-alias surface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1A.P13AKnownWheelRootMaterializerComposition/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

BASE_FORMAT = "SHIFT.P1A.P13ASlot01WheelRootMaterializationPersistenceHandoff/1"
RUNTIME_INDEX_FORMAT = "SHIFT.P1A.P13AFun00757d2cRuntimeIndexedWheelRootPersistence/1"
FIXED_FORMAT = "SHIFT.P1A.P13AFixedWheelRootLeafHandoffs/1"
TRAMP_FORMAT = "SHIFT.P1A.P13ATrampolinedWheelRootLifetime/1"
TRAMP_ALIAS_FORMAT = "SHIFT.P1A.P13AFun00760d93DerivedAliasClosure/1"
INDEXED_FORMAT = "SHIFT.P1A.P13AFun007572f0IndexedWheelRootLifetime/1"
INDEXED_ALIAS_FORMAT = "SHIFT.P1A.P13AFun00757318InteriorAliasClosure/1"

WHEEL_ROOTS = ["HDVehicle+0x400", "HDVehicle+0xe80", "HDVehicle+0x1900", "HDVehicle+0x2380"]
SLOTS = [0, 1, 2, 3]


def require(data: dict, expected: str, label: str) -> None:
    if data.get("format") != expected:
        raise ValueError(f"unexpected {label} format: {data.get('format')!r}")
    if data.get("ready") is not True:
        raise ValueError(f"{label} evidence is not ready")
    if data.get("authority", {}).get("retail_executable_sha256") != RETAIL_SHA256:
        raise ValueError(f"{label} retail executable hash drift")
    if data.get("adjudication", {}).get("external_provider_count") != 7:
        raise ValueError(f"{label} provider-count drift")


def build(base: dict, runtime_index: dict, fixed: dict, tramp: dict, tramp_alias: dict, indexed: dict, indexed_alias: dict) -> dict:
    inputs = [
        (base, BASE_FORMAT, "base"),
        (runtime_index, RUNTIME_INDEX_FORMAT, "runtime_index"),
        (fixed, FIXED_FORMAT, "fixed"),
        (tramp, TRAMP_FORMAT, "tramp"),
        (tramp_alias, TRAMP_ALIAS_FORMAT, "tramp_alias"),
        (indexed, INDEXED_FORMAT, "indexed"),
        (indexed_alias, INDEXED_ALIAS_FORMAT, "indexed_alias"),
    ]
    for data, fmt, label in inputs:
        require(data, fmt, label)

    bad_global = (
        "p13a_slot0_complete",
        "p13a_slot1_complete",
        "p1_3_control_producer_complete",
        "stored_or_escaped_aliases_ruled_out",
    )
    for data, _, label in inputs:
        adj = data["adjudication"]
        for key in bad_global:
            if adj.get(key) is not False:
                raise ValueError(f"{label} unexpectedly promotes {key}")

    base_adj = base["adjudication"]
    if base_adj.get("p13a_slot01_known_wheel_root_materialization_subset_complete") is not True:
        raise ValueError("base materialization subset incomplete")
    if base_adj.get("p13a_slot01_exact_wheel_root_nonstack_store_found") is not False:
        raise ValueError("base exact wheel-root non-stack persistence changed")

    r_adj = runtime_index["adjudication"]
    if r_adj.get("p13a_fun00757d2c_runtime_indexed_wheel_root_subset_complete") is not True:
        raise ValueError("FUN_00757d2c subset incomplete")
    if r_adj.get("runtime_indexed_exact_wheel_root_persistent_escape_found") is not False:
        raise ValueError("FUN_00757d2c exact root now escapes")
    if [row.get("slot") for row in runtime_index["runtime_identity"]["slots"]] != SLOTS:
        raise ValueError("FUN_00757d2c slot surface drift")

    f_adj = fixed["adjudication"]
    if f_adj.get("p13a_fixed_four_wheel_leaf_handoff_subset_complete") is not True:
        raise ValueError("fixed four-wheel handoff subset incomplete")
    if f_adj.get("fixed_four_wheel_leaf_root_persistence_found") is not False:
        raise ValueError("fixed four-wheel root now persists")
    if fixed["wheel_layout"].get("slots") is None or [row.get("slot") for row in fixed["wheel_layout"]["slots"]] != SLOTS:
        raise ValueError("fixed wheel layout drift")

    t_adj = tramp["adjudication"]
    if t_adj.get("p13a_trampolined_wheel_root_exact_lifetime_subset_complete") is not True:
        raise ValueError("trampolined exact-root subset incomplete")
    if t_adj.get("trampolined_exact_wheel_root_persistent_escape_found") is not False:
        raise ValueError("trampolined exact root now persists")
    if tramp["trampolined_materialization"].get("distinct_slots") != SLOTS:
        raise ValueError("trampolined slot surface drift")

    ta_adj = tramp_alias["adjudication"]
    if ta_adj.get("p13a_fun00760d93_derived_alias_subset_complete") is not True:
        raise ValueError("FUN_00760d93 derived-alias subset incomplete")
    for key in (
        "fun00760d93_derived_alias_pointer_persistence_found",
        "fun00760d93_derived_alias_selected_target_writer_found",
        "fun00760d93_derived_alias_wheel_root_reconstruction_found",
    ):
        if ta_adj.get(key) is not False:
            raise ValueError(f"FUN_00760d93 premise changed: {key}")
    if len(tramp_alias.get("aliases", {})) != 4:
        raise ValueError("FUN_00760d93 derived-alias count drift")

    i_adj = indexed["adjudication"]
    if i_adj.get("p13a_fun007572f0_indexed_wheel_root_lifetime_subset_complete") is not True:
        raise ValueError("FUN_007572f0 indexed-root subset incomplete")
    if i_adj.get("indexed_exact_wheel_root_persistent_escape_found") is not False:
        raise ValueError("FUN_007572f0 exact root now persists")
    if indexed["indexed_root"].get("formula") != "vehicle_root + 0x400 + index*0xA80":
        raise ValueError("FUN_007572f0 root formula drift")

    ia_adj = indexed_alias["adjudication"]
    if ia_adj.get("p13a_fun00757318_interior_alias_subset_complete") is not True:
        raise ValueError("FUN_00757318 interior-alias subset incomplete")
    if ia_adj.get("p13a_fun00757318_interior_alias_persistent_escape_found") is not False:
        raise ValueError("FUN_00757318 interior alias now persists")
    if indexed_alias["scope"].get("derived_alias_count") != 5:
        raise ValueError("FUN_00757318 interior-alias count drift")

    families = [
        {
            "name": "slot01_known_materializers",
            "kind": "loop+explicit",
            "source_contract": BASE_FORMAT,
            "covered_slots": [0, 1],
            "persistent_exact_root_escape_found": False,
        },
        {
            "name": "FUN_00757d2c",
            "kind": "runtime-indexed",
            "source_contract": RUNTIME_INDEX_FORMAT,
            "covered_slots": SLOTS,
            "persistent_exact_root_escape_found": False,
        },
        {
            "name": "FUN_007582f0",
            "kind": "fixed-four-wheel-leaf-handoff",
            "source_contract": FIXED_FORMAT,
            "covered_slots": SLOTS,
            "transient_handoff_count": 4,
            "persistent_exact_root_escape_found": False,
        },
        {
            "name": "FUN_0076ed60",
            "kind": "fixed-four-wheel-leaf-handoff",
            "source_contract": FIXED_FORMAT,
            "covered_slots": SLOTS,
            "transient_handoff_count": 4,
            "persistent_exact_root_escape_found": False,
        },
        {
            "name": "FUN_007653f9 -> FUN_00760d70/FUN_00760d93",
            "kind": "trampolined",
            "source_contract": TRAMP_FORMAT,
            "covered_slots": SLOTS,
            "transient_handoff_count": tramp["trampolined_materialization"]["handoff_count"],
            "persistent_exact_root_escape_found": False,
        },
        {
            "name": "FUN_007572f0/FUN_00757318",
            "kind": "runtime-indexed",
            "source_contract": INDEXED_FORMAT,
            "covered_slots": SLOTS,
            "exact_root_forward_count": indexed["exact_root_lifetime"]["exact_root_call_count"],
            "persistent_exact_root_escape_found": False,
        },
    ]

    alias_families = [
        {
            "name": "FUN_00760d93 derived aliases",
            "source_contract": TRAMP_ALIAS_FORMAT,
            "alias_count": 4,
            "persistent_alias_escape_found": False,
            "wheel_root_reconstruction_found": False,
        },
        {
            "name": "FUN_00757318 interior aliases",
            "source_contract": INDEXED_ALIAS_FORMAT,
            "alias_count": 5,
            "persistent_alias_escape_found": False,
            "wheel_root_reconstruction_found": indexed_alias["consumer_adjudication"]["any_interior_alias_reconstructed_as_root"],
        },
    ]
    if alias_families[-1]["wheel_root_reconstruction_found"] is not False:
        raise ValueError("FUN_00757318 alias unexpectedly reconstructs root")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "composition_only": True,
            "machine_proofs_remain_authoritative_upstream": True,
        },
        "upstream_contracts": [fmt for _, fmt, _ in inputs],
        "wheel_layout": {
            "count": 4,
            "roots": WHEEL_ROOTS,
            "stride": "+0xa80",
            "slots": SLOTS,
        },
        "bounded_surface": {
            "exact_root_materializer_family_count": len(families),
            "exact_root_materializer_families": families,
            "derived_alias_group_count": len(alias_families),
            "derived_alias_count": sum(row["alias_count"] for row in alias_families),
            "derived_alias_groups": alias_families,
            "known_exact_root_persistent_escape_count": 0,
            "known_derived_alias_persistent_escape_count": 0,
            "known_derived_alias_wheel_root_reconstruction_count": 0,
        },
        "adjudication": {
            "p13a_known_wheel_root_materializer_surface_composed": True,
            "p13a_known_materializer_exact_root_persistent_escape_found": False,
            "p13a_known_materializer_derived_alias_persistent_escape_found": False,
            "p13a_known_materializer_derived_alias_wheel_root_reconstruction_found": False,
            "p13a_known_materializer_all_four_wheel_slots_covered": True,
            "reconstructed_wheel_pointers_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "callbacks_and_indirect_entry_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This is a deterministic composition of seven merged P1.3A contracts; it does not discover new machine paths.",
            "The composed exact-root materializer families cover all four canonical wheel slots and show no persistent exact-root escape in those bounded families.",
            "The nine positive derived aliases already emitted by the trampolined/indexed families are also closed for persistence and wheel-root reconstruction within their bounded consumers.",
            "Unknown materializer families, runtime-generated/copied pointer stores, callbacks, incoming indirect entry and broader stored aliases remain open, so global reconstructed/slot/P1.3 gates stay fail-closed.",
        ],
        "next_step": "Enumerate residual exact-wheel-root construction/store sites outside this composed known-materializer surface, then join any positives to consumers; continue runtime callback/incoming-indirect entry independently.",
    }


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, default=Path("evidence/p1a_p13a_slot01_wheel_root_materialization_persistence_handoff.json"))
    p.add_argument("--runtime-index", type=Path, default=Path("evidence/p1a_p13a_fun00757d2c_runtime_indexed_wheel_root_persistence.json"))
    p.add_argument("--fixed", type=Path, default=Path("evidence/p1a_p13a_fixed_wheel_root_leaf_handoffs.json"))
    p.add_argument("--tramp", type=Path, default=Path("evidence/p1a_p13a_trampolined_wheel_root_lifetime.json"))
    p.add_argument("--tramp-alias", type=Path, default=Path("evidence/p1a_p13a_fun00760d93_derived_alias_closure.json"))
    p.add_argument("--indexed", type=Path, default=Path("evidence/p1a_p13a_fun007572f0_indexed_wheel_root_lifetime.json"))
    p.add_argument("--indexed-alias", type=Path, default=Path("evidence/p1a_p13a_fun00757318_interior_alias_closure.json"))
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    payload = build(load(a.base), load(a.runtime_index), load(a.fixed), load(a.tramp), load(a.tramp_alias), load(a.indexed), load(a.indexed_alias))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if a.output:
        a.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

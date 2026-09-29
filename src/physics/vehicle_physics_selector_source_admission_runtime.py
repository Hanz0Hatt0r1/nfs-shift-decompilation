"""Model selector source-record admission/scheduling from retail source."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

FORMAT = "SHIFT.VehiclePhysicsSelectorSourceAdmission/1"


def build_vehicle_physics_selector_source_admission() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "source_admission": {
            "function": "thunk_FUN_00d758d0",
            "mask_field": "owner+0x4f0",
            "selector_key": "(source_record+0x10) & 0xf",
            "bit_mask": "1 << selector_key",
            "gate": "owner+0x4f0 & bit_mask != 0",
            "on_match": [
                "ensure DAT_00bbc600 is initialized",
                "thunk_FUN_00409290(&DAT_00bbc600, source_record)",
                "owner+0x4f0 ^= bit_mask",
            ],
            "on_miss": "no selector population call and no mask mutation",
        },
        "mask_lifecycle": {
            "initialization": {
                "function": "FUN_004d4d40",
                "field": "owner+0x4f0",
                "value": 0,
            },
            "clear_and_resync": [
                {
                    "function": "FUN_004b6b30",
                    "selector_action": "thunk_FUN_00496cf0(&DAT_00bbc600, param_1)",
                    "mask_action": "owner+0x4f0 = 0",
                },
                {
                    "function": "thunk_FUN_00d75a20",
                    "selector_action": "thunk_FUN_00496cf0(&DAT_00bbc600, param_1)",
                    "mask_action": "owner+0x4f0 = 0",
                    "follow_up": "thunk_FUN_00d752b0(param_1)",
                },
            ],
        },
        "relation_to_population": {
            "population_function": "thunk_FUN_00409290",
            "population_source": "source_record+0x10",
            "capacity_gate": "selector context+0x1c < selector context+0x28",
            "descriptor_contract": "SHIFT.VehiclePhysicsSelectorDescriptorPopulation/1",
        },
        "execution_model": {
            "function": "evaluate_selector_source_admission",
            "inputs": [
                "owner+0x4f0",
                "uint32 source_record+0x10",
                "selector context+0x1c",
                "selector context+0x28",
            ],
            "outputs": [
                "selector_key",
                "bit_mask",
                "mask_hit",
                "wrapper_called",
                "capacity_available",
                "population_succeeded",
                "owner+0x4f0 after transition",
                "selector context+0x1c after transition",
            ],
            "ordering": [
                "derive low-nibble selector key",
                "test owner mask bit",
                "invoke descriptor wrapper on mask hit",
                "clear the mask bit on mask hit",
                "apply independent descriptor capacity gate",
            ],
        },
        "evidence": [
            "thunk_FUN_00d758d0 derives a selector bit from source_record+0x10 low nibble.",
            "The corresponding bit must be set in owner+0x4f0 before the source record is admitted into DAT_00bbc600.",
            "After thunk_FUN_00409290 succeeds, the same bit is cleared with XOR.",
            "FUN_004d4d40 initializes owner+0x4f0 to zero.",
            "FUN_004b6b30 and thunk_FUN_00d75a20 both resynchronize the selector and clear owner+0x4f0.",
        ],
        "limitations": [
            "The owner object and mask bits are described structurally; no gameplay subsystem name is assigned.",
            "The low-nibble key is recorded as an observed routing key, not a semantic vehicle category.",
            "No claim is made that mask admission alone guarantees successful descriptor population when the selector capacity gate is exhausted.",
        ],
    }


def evaluate_selector_source_admission(
    owner_mask: int,
    source_token: int,
    current_count: int,
    capacity: int,
) -> dict[str, Any]:
    """Evaluate the observed admission/mask/capacity state transition.

    This is an executable model of the ordering already established by the
    source-backed contract:
      1. derive the low-nibble selector key from source_record+0x10;
      2. require the corresponding owner+0x4f0 bit;
      3. call the descriptor wrapper on a mask hit;
      4. clear the hit bit;
      5. inside the wrapper, populate only while count < capacity.

    It deliberately exposes no inferred gameplay/provider semantics.
    """
    if owner_mask < 0:
        raise ValueError("owner_mask must be >= 0")
    if source_token < 0:
        raise ValueError("source_token must be >= 0")
    if current_count < 0:
        raise ValueError("current_count must be >= 0")
    if capacity < 0:
        raise ValueError("capacity must be >= 0")

    selector_key = source_token & 0xF
    bit_mask = 1 << selector_key
    mask_hit = bool(owner_mask & bit_mask)
    wrapper_called = mask_hit
    capacity_available = current_count < capacity
    population_succeeded = wrapper_called and capacity_available

    # The retail branch clears the same bit after invoking the descriptor
    # wrapper, regardless of whether the wrapper's independent capacity gate
    # accepts the record.
    next_owner_mask = owner_mask ^ bit_mask if wrapper_called else owner_mask
    next_count = current_count + 1 if population_succeeded else current_count

    return {
        "source_token": source_token,
        "selector_key": selector_key,
        "bit_mask": bit_mask,
        "mask_hit": mask_hit,
        "wrapper_called": wrapper_called,
        "capacity_available": capacity_available,
        "population_succeeded": population_succeeded,
        "mask_cleared": wrapper_called,
        "owner_mask_before": owner_mask,
        "owner_mask_after": next_owner_mask,
        "count_before": current_count,
        "count_after": next_count,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build selector source admission contract")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)
    report = build_vehicle_physics_selector_source_admission()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [\n    "FORMAT",\n    "build_vehicle_physics_selector_source_admission",\n    "evaluate_selector_source_admission",\n]

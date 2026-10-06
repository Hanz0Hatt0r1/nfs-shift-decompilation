#!/usr/bin/env python3
"""Promote a selected-session loaded rate against pinned retail identity/proof."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SNAPSHOT_FORMAT = "SHIFT.SelectedSessionPhysicsTweakerRateSnapshot/1"
CADENCE_FORMAT = "SHIFT.RetailOuterUpdateCadence/1"
OUTPUT_FORMAT = "SHIFT.SelectedSessionPhysicsTweakerRate/1"
RETAIL_EXE_SIZE = 8_801_792
RETAIL_EXE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
RETAIL_EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_ANCHORS = {
    "preferred_image_base": "0x00400000",
    "cphysics_manager_rva": "0x008104e0",
    "cphysics_manager_vtable_rva": "0x00704524",
    "post_physics_tweaker_load_flag_offset": "0x2ab",
    "physics_tweaker_tick_rate_rva": "0x008130d2",
    "manager_rate_offset": "0x388",
}


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _digest(path: Path) -> tuple[int, str, str]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            md5.update(chunk)
            sha256.update(chunk)
    return size, md5.hexdigest(), sha256.hexdigest()


def build(
    snapshot_path: Path,
    retail_exe: Path,
    cadence_path: Path,
    *,
    expected_size: int = RETAIL_EXE_SIZE,
    expected_md5: str = RETAIL_EXE_MD5,
    expected_sha256: str = RETAIL_EXE_SHA256,
) -> dict[str, Any]:
    snapshot = _load_object(snapshot_path)
    cadence = _load_object(cadence_path)

    if snapshot.get("format") != SNAPSHOT_FORMAT:
        raise ValueError(f"snapshot must be {SNAPSHOT_FORMAT}")
    if snapshot.get("ready") is not True or snapshot.get("admission_eligible") is not True:
        raise ValueError("snapshot must be admission-eligible")
    if snapshot.get("self_test") is not False:
        raise ValueError("snapshot must be a positive non-self-test runtime observation")
    if snapshot.get("anchors") != EXPECTED_ANCHORS:
        raise ValueError("snapshot retail RVA/offset anchors drifted")

    runtime_identity = snapshot.get("retail_identity")
    if not isinstance(runtime_identity, dict):
        raise ValueError("snapshot runtime retail identity missing")
    for key in (
        "pe_headers_match",
        "physics_tweaker_load_anchor_matches",
        "loaded_rate_apply_anchor_matches",
        "identity_ready",
    ):
        if runtime_identity.get(key) is not True:
            raise ValueError(f"snapshot runtime retail identity is not positive: {key}")
    if runtime_identity.get("cryptographic_hash_recomputed_at_runtime") is not False:
        raise ValueError("unexpected runtime cryptographic identity claim")
    if runtime_identity.get("pinned_pe_sha256") != RETAIL_EXE_SHA256:
        raise ValueError("snapshot runtime identity is not pinned to the expected retail SHA-256")

    selected = snapshot.get("selected_session")
    manager = snapshot.get("current_manager")
    adjudication = snapshot.get("adjudication")
    if not isinstance(selected, dict) or not isinstance(manager, dict) or not isinstance(adjudication, dict):
        raise ValueError("snapshot sections missing")

    loaded_rate = selected.get("loaded_tick_rate_hz")
    if not isinstance(loaded_rate, int) or isinstance(loaded_rate, bool) or loaded_rate <= 0:
        raise ValueError("selected-session loaded tick rate is invalid")
    if selected.get("post_load_flag") != 1:
        raise ValueError("snapshot was not taken after PhysicsTweaker load")
    if selected.get("source_backed_manager_vtable_matches") is not True:
        raise ValueError("snapshot cPhysicsManager vtable identity is not positive")
    if selected.get("stable_loaded_rate") is not True or selected.get("stable_sample_count", 0) <= 0:
        raise ValueError("selected-session loaded rate is not stable over the observation window")

    current_rate = manager.get("rate_hz")
    if not isinstance(current_rate, int) or isinstance(current_rate, bool):
        raise ValueError("current manager rate observation is malformed")
    relationships_valid = manager.get("relationships_valid") is True
    equals_loaded = (
        manager.get("equals_loaded_tick_rate") is True
        and current_rate == loaded_rate
    )

    if adjudication.get("physics_tweaker_xml_load_completed_before_observation") is not True:
        raise ValueError("snapshot does not prove PhysicsTweaker.xml load completion")
    if adjudication.get("loaded_global_applied_to_cphysics_manager_at_initialization") is not True:
        raise ValueError("snapshot lost the static loaded-global application anchor")
    if adjudication.get("selected_session_loaded_rate_observed_after_PhysicsTweaker_load") is not True:
        raise ValueError("snapshot does not positively adjudicate post-load observation")
    if adjudication.get("constructor_default_180_used_as_admission_basis") is not False:
        raise ValueError("constructor default was used as an admission basis")
    if adjudication.get("current_manager_rate_is_assumed_constant") is not False:
        raise ValueError("snapshot incorrectly assumes the manager rate is permanently constant")
    if adjudication.get("retail_inner_substep_execution_admitted") is not False:
        raise ValueError("raw snapshot must not pre-admit inner substep execution")

    if cadence.get("format") != CADENCE_FORMAT or cadence.get("ready") is not True:
        raise ValueError(f"cadence input must be positive {CADENCE_FORMAT}")
    provenance = cadence.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("cadence provenance missing")
    if (
        provenance.get("retail_pe_md5") != RETAIL_EXE_MD5
        or provenance.get("retail_pe_sha256") != RETAIL_EXE_SHA256
    ):
        raise ValueError("cadence proof is not pinned to the expected retail executable")
    rate_static = cadence.get("physics_rate_field")
    if (
        not isinstance(rate_static, dict)
        or rate_static.get("runtime_rate_global") != "DAT_00c130d2"
    ):
        raise ValueError("cadence proof no longer identifies DAT_00c130d2 as the loaded rate alias")
    if (
        rate_static.get("rate_offset") != "0x388"
        or rate_static.get("final_numeric_rate_not_frozen") is not True
    ):
        raise ValueError("cadence rate-domain boundary drifted")

    size, md5, sha256 = _digest(retail_exe)
    if size != expected_size:
        raise ValueError(f"retail executable size mismatch: expected {expected_size}, got {size}")
    if md5 != expected_md5:
        raise ValueError(f"retail executable MD5 mismatch: expected {expected_md5}, got {md5}")
    if sha256 != expected_sha256:
        raise ValueError(f"retail executable SHA-256 mismatch: expected {expected_sha256}, got {sha256}")

    if current_rate <= 0 or not relationships_valid:
        next_blocker = "current-manager-rate-observation-coherence"
    elif not equals_loaded:
        next_blocker = "current-manager-rate-scheduling-policy"
    else:
        next_blocker = "inner-substep-runtime-consumption"

    return {
        "format": OUTPUT_FORMAT,
        "version": 1,
        "status": "selected-session-loaded-rate-admitted",
        "ready": True,
        "blocker": "selected-session-physics-tweaker-rate-admission",
        "retail_identity": {
            "size": size,
            "md5": md5,
            "sha256": sha256,
            "exact_match": True,
            "runtime_pe_and_machine_anchors_match": True,
        },
        "static_join": {
            "cadence_format": CADENCE_FORMAT,
            "runtime_rate_global": "DAT_00c130d2",
            "manager_rate_offset": "0x388",
            "inner_substep_expression": "1/rate",
            "outer_cadence_remains_separate": True,
            "loaded_global_applied_to_manager_at_initialization": True,
        },
        "selected_session": {
            "loaded_tick_rate_hz": loaded_rate,
            "observation_sample_count": selected["stable_sample_count"],
            "observed_after_physics_tweaker_load": True,
            "constructor_default_180_is_not_admission_basis": True,
        },
        "current_manager_observation": {
            "rate_hz": current_rate,
            "equals_loaded_tick_rate": equals_loaded,
            "relationships_valid": relationships_valid,
            "admission_dependency": False,
        },
        "adjudication": {
            "selected_session_loaded_rate_admitted": True,
            "current_manager_rate_assumed_permanently_equal_to_loaded_rate": False,
            "dynamic_manager_rate_policy_proven": False,
            "retail_inner_substep_execution_admitted": False,
        },
        "limits": {
            "host_1_60_promoted": False,
            "outer_33ms_gate_used_as_inner_dt": False,
            "constructor_default_180_promoted_without_runtime_observation": False,
            "rendered_frame_equivalence_claimed": False,
        },
        "next_blocker": next_blocker,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("retail_exe", type=Path)
    parser.add_argument(
        "--cadence",
        type=Path,
        default=Path("evidence/s5_retail_outer_update_cadence.json"),
    )
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()

    report = build(args.snapshot, args.retail_exe, args.cadence)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

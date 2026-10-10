#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "evidence/hdvehicle_64e8_manager_374_static_pointer_occurrence_surface.json"
SIMPLE = ROOT / "evidence/hdvehicle_64e8_manager_374_simple_arithmetic_reconstruction_surface.json"
MULTI = ROOT / "evidence/hdvehicle_64e8_manager_374_constant_multireg_reconstruction_surface.json"
ALIASES = ROOT / "evidence/p1b_manager374_exact_root_alias_closure.json"
OUT = ROOT / "evidence/p1b_manager374_reconstruction_coverage.json"


def load(path):
    return json.loads(path.read_text())


def build():
    static = load(STATIC)
    simple = load(SIMPLE)
    multi = load(MULTI)
    aliases = load(ALIASES)
    assert static["format"] == "SHIFT.HDVehicle64e8Manager374StaticPointerOccurrenceSurface/1"
    assert simple["format"] == "SHIFT.HDVehicle64e8Manager374SimpleArithmeticReconstructionSurface/1"
    assert multi["format"] == "SHIFT.HDVehicle64e8Manager374ConstantMultiRegisterReconstructionSurface/1"
    assert aliases["format"] == "SHIFT.P1B.Manager374ExactRootAliasClosure/1"
    assert static["adjudication"]["static_exact_pointer_cell_surface_complete"] is True
    assert static["adjudication"]["static_exact_pointer_cell_count"] == 0
    assert simple["adjudication"]["simple_immediate_arithmetic_reconstruction_surface_complete"] is True
    assert simple["adjudication"]["simple_non_literal_reconstruction_site_count"] == 0
    assert multi["adjudication"]["constant_only_multi_register_reconstruction_surface_complete"] is True
    assert multi["adjudication"]["constant_only_non_literal_manager_root_count"] == 0
    return {
        "format": "SHIFT.P1B.Manager374ReconstructionCoverage/1",
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1",
        },
        "upstream_contracts": [static["format"], simple["format"], multi["format"], aliases["format"]],
        "surface": {
            "static_exact_pointer_cell_count": 0,
            "simple_mov_immediate_seed_count": simple["scan"]["mov_immediate_seed_count"],
            "simple_arithmetic_transition_count": simple["scan"]["same_register_arithmetic_transition_count"],
            "simple_non_literal_exact_root_count": simple["scan"]["non_literal_chains_reconstructing_exact_singleton_count"],
            "constant_multi_register_transition_count": multi["scan"]["constant_arithmetic_transition_count"],
            "constant_multi_register_non_literal_exact_root_count": multi["scan"]["non_literal_exact_root_production_count"],
        },
        "adjudication": {
            "static_exact_pointer_cells_complete": True,
            "simple_immediate_arithmetic_reconstruction_complete": True,
            "constant_only_multi_register_reconstruction_complete": True,
            "bounded_non_literal_manager_root_reconstruction_count": 0,
            "bounded_reconstruction_classes_can_create_unrelated_manager_root": False,
            "memory_load_or_opaque_runtime_reconstruction_complete": False,
            "helper_or_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes only static exact-pointer cells, simple same-register immediate arithmetic, and constant-only multi-register synthesis.",
            "Memory-load-derived, externally initialized, relocated, opaque helper-return, indirect-call, and unrecognized transform paths remain open.",
            "No identity is inferred from numeric offset equality.",
        ],
        "next_step": "Close memory-load/opaque-runtime manager-root reconstruction and helper/non-vtable indirect setters; then perform the final manager+0x374 -> HDVehicle+0x4330 identity join and 0x004b86cf / slot2 adjudication.",
    }


def main():
    payload = build()
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    import sys
    if "--check" in sys.argv:
        assert OUT.read_text() == text
    else:
        OUT.write_text(text)


if __name__ == "__main__":
    main()

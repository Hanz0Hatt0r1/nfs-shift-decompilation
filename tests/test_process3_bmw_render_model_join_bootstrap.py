from __future__ import annotations

import copy

import pytest

import bmw_vehicle_render_model_resource_join as join_mod
import bmw_vhf_body_world_transform as vhf_mod


MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
MEB_SHA = "9" * 64


def _observed_from_join(join):
    canonical = join["canonical_bmw_vhf_resource"]
    return {
        "archive": canonical["archive"],
        "archive_sha256": canonical["archive_sha256"],
        "entry_index": canonical["entry_index"],
        "path": canonical["resolved_path"],
        "decoded_sha256": canonical["decoded_sha256"],
        "decoded_size": canonical["uncompressed_size"],
    }


def test_positive_resource_join_selects_exact_primary_vhf():
    join = join_mod.load_bmw_vehicle_render_model_resource_join()
    canonical = join["canonical_bmw_vhf_resource"]

    assert canonical["resolved_path"] == "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
    assert canonical["archive"] == "BMW_M3_E36.bff"
    assert join["selected_vehicle_descriptor"]["property_value"] == "BMW_M3_E36.vhf"
    assert join["scope"]["basename_only_fallback_used"] is False
    assert join["negative_disambiguation"][
        "cockpit_does_not_match_selected_vehicle_render_model"
    ] is True


def test_cockpit_vhf_cannot_satisfy_primary_resource_join():
    join = join_mod.load_bmw_vehicle_render_model_resource_join()
    observed = _observed_from_join(join)
    observed["path"] = join["negative_disambiguation"]["cockpit_vhf_path"]
    observed["archive"] = "BMW_M3_E36_Cockpit.bff"
    observed["archive_sha256"] = join["negative_disambiguation"][
        "BMW_M3_E36_Cockpit.bff_sha256"
    ]

    with pytest.raises(ValueError):
        join_mod.validate_vhf_identity_against_render_model_join(observed, join)


def test_vhf_transform_consumes_join_and_revalidates_observed_identity(monkeypatch):
    join = join_mod.load_bmw_vehicle_render_model_resource_join()
    observed = _observed_from_join(join)
    monkeypatch.setattr(vhf_mod, "_vhf_source_identity", lambda *a, **k: observed)
    monkeypatch.setattr(
        vhf_mod,
        "build_vhf_scene",
        lambda *a, **k: {
            "format": "SHIFT.VHFScene/1",
            "parts": [{
                "name": vhf_mod.DEFAULT_BODY_NODE,
                "resource": MEB,
                "resource_sha256": MEB_SHA,
                "matrix_number": "17",
                "world_matrix": [
                    1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    0.0, 0.0, 0.0, 1.0,
                ],
            }],
        },
    )
    golden = {
        "format": "SHIFT.BMWGoldenAssetManifest/1",
        "golden": {"resource": MEB, "resource_sha256": MEB_SHA},
    }

    report = vhf_mod.build_bmw_vhf_body_world_transform(
        "BMW_M3_E36.bff",
        golden,
        vhf_resource=join["canonical_bmw_vhf_resource"]["resolved_path"],
        vehicle_render_model_join=join,
    )

    assert report["ready"] is True
    assert report["source"]["vhf_entry"] == observed
    assert report["source"]["vehicle_render_model_resource_join"]["ready"] is True
    assert report["boundary"]["bmw_vehicle_render_model_resource_join_consumed"] is True
    assert report["boundary"]["basename_fallback_allowed_for_primary_vhf"] is False
    assert report["boundary"]["cockpit_vhf_substitution_allowed"] is False


def test_resource_join_rejects_primary_path_rewritten_to_cockpit():
    join = join_mod.load_bmw_vehicle_render_model_resource_join()
    mutated = copy.deepcopy(join)
    mutated["canonical_bmw_vhf_resource"]["resolved_path"] = (
        mutated["negative_disambiguation"]["cockpit_vhf_path"]
    )

    with pytest.raises(ValueError, match="canonical BMW VHF path"):
        join_mod.load_bmw_vehicle_render_model_resource_join(mutated)

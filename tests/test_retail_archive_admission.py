from __future__ import annotations

import retail_archive_admission as admission
from retail_archive_identity import track_archive_identity, vehicle_archive_identity


def _row(archive_id, identity, source):
    return {
        "id": archive_id,
        "archive_name": identity.archive_name,
        "sha256": identity.sha256,
        "source": source,
        "source_member": identity.archive_name,
        "source_kind": "zip-member",
    }


def _fixture():
    track_visual = track_archive_identity("Silverstone_Era3_GrandPrix", "visual")
    track_physics = track_archive_identity("Silverstone_Era3_GrandPrix", "physics")
    vehicle = vehicle_archive_identity("BMW_M3_E36", "primary")
    cockpit = vehicle_archive_identity("BMW_M3_E36", "cockpit")
    assert track_visual and track_physics and vehicle and cockpit
    rows = [
        _row("tv", track_visual, "Silverstone_Era3_.zip"),
        _row("tp", track_physics, "Silverstone_Era3_.zip"),
        _row("veh", vehicle, "Vehicles.zip"),
        _row("cockpit", cockpit, "Vehicles.zip"),
    ]
    catalog = {"format": "SHIFT.OfflineResourceCatalog/1", "archives": rows}
    bootstrap = {
        "format": "SHIFT.SceneVehicleBootstrap/1",
        "ready": True,
        "selected_archives": {
            "track_visual": rows[0],
            "track_physics": rows[1],
            "vehicle": rows[2],
            "vehicle_cockpit": rows[3],
        },
        "blocking_reasons": [],
    }
    return catalog, bootstrap


def test_current_playable_target_requires_exact_hash_and_unique_occurrence():
    catalog, bootstrap = _fixture()
    report = admission.build_retail_archive_identity_admission(
        catalog,
        bootstrap,
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
    )

    assert report["ready"] is True
    assert report["blocking_reasons"] == []
    assert set(report["roles"]) == {
        "track_visual",
        "track_physics",
        "vehicle_primary",
        "vehicle_cockpit",
    }
    assert all(row["ready"] is True for row in report["roles"].values())
    assert report["boundary"]["archive_basename_is_identity_proof"] is False
    assert report["boundary"]["retail_sha256_required"] is True
    assert report["boundary"]["byte_identical_duplicate_collapse_allowed"] is False


def test_selected_archive_hash_mismatch_is_blocking():
    catalog, bootstrap = _fixture()
    bootstrap["selected_archives"]["vehicle"] = {
        **bootstrap["selected_archives"]["vehicle"],
        "sha256": "0" * 64,
    }

    report = admission.build_retail_archive_identity_admission(
        catalog,
        bootstrap,
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
    )

    assert report["ready"] is False
    assert any(
        reason.startswith("retail-archive-sha256-mismatch:vehicle_primary:")
        for reason in report["blocking_reasons"]
    )


def test_byte_identical_duplicate_occurrence_remains_ambiguous():
    catalog, bootstrap = _fixture()
    duplicate = dict(catalog["archives"][2])
    duplicate["id"] = "veh-duplicate"
    duplicate["source"] = "second-copy.zip"
    catalog["archives"].append(duplicate)

    report = admission.build_retail_archive_identity_admission(
        catalog,
        bootstrap,
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
    )

    assert report["ready"] is False
    assert (
        "retail-archive-exact-occurrence-ambiguous:2:vehicle_primary:BMW_M3_E36.bff"
        in report["blocking_reasons"]
    )


def test_unknown_target_does_not_fall_back_to_name_only_identity():
    report = admission.build_retail_archive_identity_admission(
        {"archives": []},
        {"ready": True, "selected_archives": {}, "blocking_reasons": []},
        track="Unknown_Track",
        vehicle="Unknown_Car",
    )

    assert report["ready"] is False
    assert "retail-archive-identity-unavailable:track_visual" in report["blocking_reasons"]
    assert "retail-archive-identity-unavailable:vehicle_primary" in report["blocking_reasons"]

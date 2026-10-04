from __future__ import annotations

import hashlib
from pathlib import Path

import offline_native_vehicle as vehicle


KINDS = ("cdf", "edf", "gdf", "sdf", "tbf", "bbf")


def _inputs(tmp_path: Path):
    resources = []
    roots = {}
    bundle_entries = {}
    profile_resources = {}
    typed_rows = []
    for index, kind in enumerate(KINDS, 20):
        payload = f"payload-{kind}-{index}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        raw_digest = hashlib.sha256(b"raw-" + payload).hexdigest()
        resource_id = f"vehicle#{index}"
        retail_path = f"vehicles/physics/{kind}/fixture.{kind}"
        materialized = tmp_path / "typed" / retail_path
        materialized.parent.mkdir(parents=True, exist_ok=True)
        materialized.write_bytes(payload)
        resources.append({
            "id": resource_id,
            "archive_id": "vehicle",
            "archive_name": "BMW_M3_E36.bff",
            "index": index,
            "path": retail_path,
            "compression_type": 2,
            "compressed_size": 100 + index,
            "uncompressed_size": len(payload),
        })
        roots[f".{kind}"] = resource_id
        bundle_entries[kind] = {
            "archive_path": retail_path,
            "index": index,
            "type": 2,
            "compressed_size": 100 + index,
            "uncompressed_size": len(payload),
            "decoded_sha256": digest,
            "raw_sha256": raw_digest,
        }
        if kind in {"cdf", "edf", "gdf", "sdf"}:
            profile_resources[kind] = {"sha256": digest}
        typed_rows.append({
            "resource_id": resource_id,
            "path": retail_path,
            "output": str(materialized),
            "decoded_sha256": digest,
            "catalog_decoded_sha256": digest,
            "identity_match": True,
        })

    catalog = {"format": "SHIFT.OfflineResourceCatalog/1", "resources": resources}
    bootstrap = {
        "format": "SHIFT.SceneVehicleBootstrap/1",
        "ready": True,
        "vehicle": "BMW_M3_E36",
        "selected_archives": {
            "vehicle": {"id": "vehicle", "archive_name": "BMW_M3_E36.bff"},
        },
        "roots": {"vehicle": roots},
    }
    physics = {
        "format": "SHIFT.VehiclePhysicsBundleExtractor/1",
        "ready": True,
        "source": {"bff": "/retail/BMW_M3_E36.bff"},
        "entries": bundle_entries,
        "profile": {
            "format": "SHIFT.VehiclePhysicsAssetGraph/1",
            "ready": True,
            "resources": profile_resources,
            "summary": {
                "sdf_bodies": 11,
                "sdf_joint_hinge_count": 4,
                "sdf_bar_count": 20,
            },
        },
    }
    closure = {
        "format": "SHIFT.TypedResourceClosure/1",
        "ready": True,
        "resources": typed_rows,
    }
    return catalog, bootstrap, physics, closure


def test_native_vehicle_uses_exact_typed_physics_paths(tmp_path):
    catalog, bootstrap, physics, closure = _inputs(tmp_path)
    report = vehicle.build_native_vehicle(
        catalog,
        bootstrap,
        physics,
        typed_closure=closure,
    )

    assert report["resource_ready"] is True
    assert report["runtime_physics_contract_ready"] is True
    assert report["vehicle_physics_manifest"]["materialized_resources_ready"] is True
    assert set(report["materialized_physics_resources"]) == set(KINDS)
    sdf = report["materialized_physics_resources"]["sdf"]
    assert sdf["path"].endswith("fixture.sdf")
    assert Path(sdf["materialized_path"]).is_file()
    assert report["boundary"]["typed_resource_closure_evaluated"] is True
    assert report["boundary"]["typed_physics_materializations_ready"] is True
    assert report["boundary"]["body_semantics_claimed_by_materialization_handoff"] is False

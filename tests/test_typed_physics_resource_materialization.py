from __future__ import annotations

import hashlib
from pathlib import Path

from typed_physics_resource_materialization import (
    PHYSICS_KINDS,
    PHYSICS_MANIFEST_FORMAT,
    TYPED_CLOSURE_FORMAT,
    attach_typed_physics_materializations,
)


def _fixture(tmp_path: Path):
    entries = {}
    resources = []
    paths = {}
    for index, kind in enumerate(PHYSICS_KINDS, 20):
        payload = f"retail-{kind}-payload-{index}\n".encode("ascii")
        path = tmp_path / "typed_resources" / "BMW_M3_E36.bff" / f"fixture.{kind}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        resource_id = f"bff-vehicle#{index}"
        retail_path = f"vehicles/physics/{kind}/fixture.{kind}"
        entries[kind] = {
            "resource_id": resource_id,
            "path": retail_path,
            "entry_index": index,
            "type": 2,
            "compressed_size": 100 + index,
            "uncompressed_size": len(payload),
            "decoded_sha256": digest,
            "raw_sha256": hashlib.sha256(b"raw-" + payload).hexdigest(),
        }
        resources.append({
            "resource_id": resource_id,
            "archive": "BMW_M3_E36.bff",
            "path": retail_path,
            "output": str(path),
            "decoded_sha256": digest,
            "catalog_decoded_sha256": digest,
            "identity_match": True,
        })
        paths[kind] = path

    manifest = {
        "format": PHYSICS_MANIFEST_FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "vehicle": "BMW_M3_E36",
        "entries": entries,
        "source": {},
        "boundary": {
            "runtime_provider_identity_claimed": False,
            "runtime_schedule_claimed": False,
        },
    }
    closure = {
        "format": TYPED_CLOSURE_FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "resources": resources,
    }
    return manifest, closure, paths


def test_exact_typed_closure_attaches_persistent_physics_paths(tmp_path):
    manifest, closure, paths = _fixture(tmp_path)
    report = attach_typed_physics_materializations(manifest, closure)

    assert report["format"] == PHYSICS_MANIFEST_FORMAT
    assert report["ready"] is True
    assert report["status"] == "ready"
    assert report["blocking_reasons"] == []
    assert report["materialized_resource_count"] == len(PHYSICS_KINDS)
    assert report["materialized_resources_ready"] is True
    assert report["entries"]["sdf"]["materialized_path"] == str(paths["sdf"])
    assert report["entries"]["sdf"]["materialized_sha256"] == hashlib.sha256(
        paths["sdf"].read_bytes()
    ).hexdigest()
    assert report["boundary"]["typed_resource_materialized_paths_ready"] is True
    assert report["boundary"]["basename_fallback_used"] is False
    assert report["boundary"]["resource_similarity_used"] is False
    assert report["boundary"]["body_semantics_claimed"] is False
    assert report["boundary"]["participant_identity_claimed"] is False


def test_materialized_file_hash_drift_fails_closed(tmp_path):
    manifest, closure, paths = _fixture(tmp_path)
    paths["sdf"].write_bytes(b"changed after typed closure\n")

    report = attach_typed_physics_materializations(manifest, closure)

    assert report["ready"] is False
    assert report["materialized_resources_ready"] is False
    assert "sdf:typed-resource-file-sha256-mismatch" in report["blocking_reasons"]
    assert "materialized_path" not in report["entries"]["sdf"]


def test_duplicate_resource_id_is_ambiguous_even_for_identical_bytes(tmp_path):
    manifest, closure, _ = _fixture(tmp_path)
    duplicate = dict(closure["resources"][3])
    closure["resources"].append(duplicate)

    report = attach_typed_physics_materializations(manifest, closure)

    assert report["ready"] is False
    assert any(
        reason.startswith("sdf:typed-resource-ambiguous:2:")
        for reason in report["blocking_reasons"]
    )
    assert "materialized_path" not in report["entries"]["sdf"]


def test_similar_basename_cannot_replace_exact_retail_path(tmp_path):
    manifest, closure, _ = _fixture(tmp_path)
    closure["resources"][3] = dict(closure["resources"][3])
    closure["resources"][3]["path"] = "other/location/fixture.sdf"

    report = attach_typed_physics_materializations(manifest, closure)

    assert report["ready"] is False
    assert "sdf:typed-resource-path-mismatch" in report["blocking_reasons"]
    assert "materialized_path" not in report["entries"]["sdf"]

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from retail_archive_materialization import materialize_admitted_archive_role
from selected_archive_materialization import materialize_selected_archive


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _admission(*, source: Path, source_kind: str, member: str | None, data: bytes):
    return {
        "format": "SHIFT.RetailArchiveIdentityAdmission/1",
        "ready": True,
        "roles": {
            "vehicle_primary": {
                "role": "vehicle_primary",
                "ready": True,
                "expected_identity": {
                    "archive_name": "BMW_M3_E36.bff",
                    "sha256": _sha(data),
                },
                "admitted_occurrence": {
                    "id": "vehicle-archive",
                    "source": str(source),
                    "source_member": member,
                    "source_kind": source_kind,
                    "archive_name": "BMW_M3_E36.bff",
                    "sha256": _sha(data),
                    "bytes": len(data),
                },
            },
        },
    }


def test_exact_zip_member_is_materialized_without_basename_fallback(tmp_path):
    wanted = b"exact retail BMW archive bytes"
    decoy = b"wrong archive with same basename"
    source = tmp_path / "Vehicles.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("retail/BMW_M3_E36.bff", wanted)
        archive.writestr("decoy/BMW_M3_E36.bff", decoy)

    report = materialize_admitted_archive_role(
        _admission(
            source=source,
            source_kind="zip-member",
            member="retail/BMW_M3_E36.bff",
            data=wanted,
        ),
        role="vehicle_primary",
        output_dir=tmp_path / "out",
    )

    assert report["ready"] is True
    path = Path(report["path"])
    assert path.read_bytes() == wanted
    assert report["sha256"] == _sha(wanted)
    assert report["boundary"]["basename_fallback_used"] is False
    assert report["boundary"]["archive_order_used"] is False


def test_zip_member_hash_drift_fails_closed(tmp_path):
    expected = b"expected"
    source = tmp_path / "Vehicles.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("BMW_M3_E36.bff", b"changed")

    report = materialize_admitted_archive_role(
        _admission(
            source=source,
            source_kind="zip-member",
            member="BMW_M3_E36.bff",
            data=expected,
        ),
        role="vehicle_primary",
        output_dir=tmp_path / "out",
    )

    assert report["ready"] is False
    assert any("SHA-256 drift" in reason for reason in report["blocking_reasons"])
    assert report["path"] is None


def test_directory_source_requires_one_exact_name_and_hash_occurrence(tmp_path):
    data = b"identical exact bytes"
    source = tmp_path / "Vehicles"
    for name in ("one", "two"):
        path = source / name / "BMW_M3_E36.bff"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    report = materialize_admitted_archive_role(
        _admission(
            source=source,
            source_kind="directory-bff",
            member=None,
            data=data,
        ),
        role="vehicle_primary",
        output_dir=tmp_path / "out",
    )

    assert report["ready"] is False
    assert any("ambiguous:2" in reason for reason in report["blocking_reasons"])


def test_selected_catalog_occurrence_join_uses_exact_id_and_provenance(tmp_path):
    data = b"catalog-selected BMW archive"
    source = tmp_path / "BMW_M3_E36.bff"
    source.write_bytes(data)
    catalog = {
        "format": "SHIFT.OfflineResourceCatalog/1",
        "archives": [{
            "id": "vehicle-archive",
            "source": str(source),
            "source_member": None,
            "source_kind": "bff",
            "archive_name": source.name,
            "sha256": _sha(data),
            "bytes": len(data),
        }],
    }
    bootstrap = {
        "format": "SHIFT.SceneVehicleBootstrap/1",
        "selected_archives": {
            "vehicle": {
                "id": "vehicle-archive",
                "archive_name": source.name,
                "sha256": _sha(data),
            },
        },
    }

    report = materialize_selected_archive(
        catalog,
        bootstrap,
        selected_key="vehicle",
        role="vehicle_primary",
        output_dir=tmp_path / "out",
    )

    assert report is not None and report["ready"] is True
    assert Path(report["path"]).read_bytes() == data
    assert report["boundary"]["catalog_selected_occurrence_join_required"] is True
    assert report["boundary"]["canonical_retail_identity_claimed_here"] is False


def test_legacy_catalog_without_source_provenance_skips_materialization():
    catalog = {
        "format": "SHIFT.OfflineResourceCatalog/1",
        "archives": [{
            "id": "vehicle-archive",
            "archive_name": "BMW_M3_E36.bff",
            "sha256": "a" * 64,
        }],
    }
    bootstrap = {
        "format": "SHIFT.SceneVehicleBootstrap/1",
        "selected_archives": {
            "vehicle": {
                "id": "vehicle-archive",
                "archive_name": "BMW_M3_E36.bff",
                "sha256": "a" * 64,
            },
        },
    }
    assert materialize_selected_archive(
        catalog,
        bootstrap,
        selected_key="vehicle",
        role="vehicle_primary",
        output_dir="unused",
    ) is None

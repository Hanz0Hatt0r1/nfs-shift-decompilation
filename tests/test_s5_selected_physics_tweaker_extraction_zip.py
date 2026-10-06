from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/materialize_s5_selected_physics_tweaker_from_extraction_zip.py"
SPEC = importlib.util.spec_from_file_location(
    "materialize_s5_selected_physics_tweaker_from_extraction_zip", TOOL
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _identity(size: int = 7) -> dict:
    return {
        "archive": {
            "filename": "PHYSICSBOOTFLOW.bff",
            "sha256": "f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a",
        },
        "entry": {
            "index": 49,
            "path": "vehicles/physics/physicstweaker.xml",
            "compression_type": 2,
            "compressed_size": 2452,
            "uncompressed_size": size,
            "decoded_sha256": "6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f",
        },
    }


def _write_zip(
    path: Path,
    *,
    prefix: str = "",
    payload: bytes = b"fixture",
    manifest_member: str | None = None,
    decoded_member: str | None = None,
    extra: dict[str, bytes] | None = None,
) -> None:
    prefix = prefix.strip("/")
    root = f"{prefix}/" if prefix else ""
    manifest_member = manifest_member or f"{root}_bff_manifest.csv"
    decoded_member = decoded_member or f"{root}vehicles/physics/physicstweaker.xml"
    manifest = (
        "index,name,offset,compressed_size,size,type,method,crc_field,extension_field,status\n"
        "49,vehicles\\physics\\physicstweaker.xml,0x31800,2452,21762,2,"
        "xmem/lzx:1frame(s),0xa0f8c093,xml,ok\n"
    ).encode()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(manifest_member, manifest)
        archive.writestr(decoded_member, payload)
        for name, data in (extra or {}).items():
            archive.writestr(name, data)


def test_zip_adapter_binds_manifest_and_xml_under_same_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    payload = b"fixture"
    archive_path = tmp_path / "PHYSICSBOOTFLOW_extracted.zip"
    _write_zip(archive_path, prefix="PHYSICSBOOTFLOW.extracted", payload=payload)
    monkeypatch.setattr(MODULE, "_resource_identity", lambda _path: _identity(len(payload)))

    calls: list[tuple[Path, Path]] = []

    def fake_tree_adapter(
        _geometry: Path,
        _cadence: Path,
        extracted_root: Path,
        manifest_path: Path,
    ) -> dict:
        assert manifest_path.name == "_bff_manifest.csv"
        assert b"physicstweaker.xml" in manifest_path.read_bytes().lower()
        decoded = extracted_root / "vehicles/physics/physicstweaker.xml"
        assert decoded.read_bytes() == payload
        calls.append((extracted_root, manifest_path))
        return {
            "format": "SHIFT.SelectedSessionPhysicsTweakerRate/1",
            "ready": True,
            "status": "selected-session-physics-tweaker-rate-ready",
            "verification": {
                "mode": "exact-extracted-entry-manifest",
                "archive_sha256_verified_this_run": False,
                "decoded_sha256_verified_this_run": True,
                "extraction_manifest_verified_this_run": True,
            },
            "selected_session_rate": {"rate_hz": 1},
        }

    monkeypatch.setattr(MODULE, "materialize_from_extraction", fake_tree_adapter)
    report = MODULE.materialize_from_extraction_zip(
        tmp_path / "geometry.json",
        tmp_path / "cadence.json",
        archive_path,
    )

    assert len(calls) == 1
    verification = report["verification"]
    assert verification["mode"] == "exact-extracted-zip-manifest"
    assert verification["archive_sha256_verified_this_run"] is False
    assert verification["decoded_sha256_verified_this_run"] is True
    assert verification["extraction_zip_member_layout_verified_this_run"] is True
    assert verification["extraction_zip_manifest_member"] == (
        "PHYSICSBOOTFLOW.extracted/_bff_manifest.csv"
    )
    assert verification["extraction_zip_decoded_member"] == (
        "PHYSICSBOOTFLOW.extracted/vehicles/physics/physicstweaker.xml"
    )


def test_zip_adapter_rejects_xml_outside_manifest_root(tmp_path: Path):
    archive_path = tmp_path / "split.zip"
    _write_zip(
        archive_path,
        prefix="bundle",
        decoded_member="vehicles/physics/physicstweaker.xml",
    )
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(ValueError, match="manifest root"):
            MODULE._select_bound_members(archive, _identity())


def test_zip_adapter_rejects_multiple_manifests(tmp_path: Path):
    archive_path = tmp_path / "duplicate-manifest.zip"
    _write_zip(
        archive_path,
        extra={"other/_bff_manifest.csv": b"duplicate\n"},
    )
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(ValueError, match="exactly one extraction ZIP manifest"):
            MODULE._select_bound_members(archive, _identity())


def test_zip_adapter_rejects_unsafe_member_path(tmp_path: Path):
    archive_path = tmp_path / "unsafe.zip"
    _write_zip(archive_path, extra={"../escape.txt": b"no"})
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(ValueError, match="unsafe ZIP member path"):
            MODULE._select_bound_members(archive, _identity())


def test_zip_adapter_rejects_decoded_member_size_before_tree_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    archive_path = tmp_path / "wrong-size.zip"
    _write_zip(archive_path, payload=b"short")
    monkeypatch.setattr(MODULE, "_resource_identity", lambda _path: _identity(123))
    with pytest.raises(ValueError, match="ZIP member size mismatch"):
        MODULE.materialize_from_extraction_zip(
            tmp_path / "geometry.json",
            tmp_path / "cadence.json",
            archive_path,
        )


def test_zip_adapter_never_substitutes_a_tick_rate_literal():
    source = TOOL.read_text(encoding="utf-8")
    assert "decoded SHA-256 + unique" in source
    assert "materialize_from_extraction(" in source
    assert "rate_hz = 180" not in source
    assert "rate_hz = 360" not in source

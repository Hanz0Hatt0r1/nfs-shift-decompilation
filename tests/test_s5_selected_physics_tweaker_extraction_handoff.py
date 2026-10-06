from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/materialize_s5_selected_physics_tweaker_from_extraction.py"
SPEC = importlib.util.spec_from_file_location(
    "materialize_s5_selected_physics_tweaker_from_extraction", TOOL
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _identity() -> dict:
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
            "uncompressed_size": 21762,
            "decoded_sha256": "6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f",
        },
    }


def _manifest_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "index": 49,
        "name": r"vehicles\physics\physicstweaker.xml",
        "offset": "0x31800",
        "compressed_size": 2452,
        "size": 21762,
        "type": 2,
        "method": "xmem/lzx:1frame(s)",
        "crc_field": "0xa0f8c093",
        "extension_field": "xml",
        "status": "ok",
    }
    row.update(overrides)
    return row


def _write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "index",
        "name",
        "offset",
        "compressed_size",
        "size",
        "type",
        "method",
        "crc_field",
        "extension_field",
        "status",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_extracted_entry(root: Path, payload: bytes = b"fixture") -> Path:
    path = root / "vehicles/physics/physicstweaker.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_resolves_successful_type2_manifest_entry_exactly(tmp_path: Path):
    root = tmp_path / "extracted"
    expected_path = _write_extracted_entry(root)
    manifest = tmp_path / "_bff_manifest.csv"
    _write_manifest(manifest, [_manifest_row()])

    decoded_path, metadata = MODULE.resolve_extracted_entry(
        root, manifest, _identity()
    )

    assert decoded_path == expected_path
    assert metadata == {
        "entry_index": 49,
        "entry_path": "vehicles/physics/physicstweaker.xml",
        "compression_type": 2,
        "compressed_size": 2452,
        "uncompressed_size": 21762,
        "method": "xmem/lzx:1frame(s)",
        "status": "ok",
        "crc_field": "0xa0f8c093",
    }


def test_rejects_manifest_metadata_drift_before_decoded_hash_admission(
    tmp_path: Path,
):
    root = tmp_path / "extracted"
    _write_extracted_entry(root)
    manifest = tmp_path / "_bff_manifest.csv"
    _write_manifest(manifest, [_manifest_row(compressed_size=2453)])

    with pytest.raises(ValueError, match="manifest metadata mismatch"):
        MODULE.resolve_extracted_entry(root, manifest, _identity())


def test_rejects_non_ok_or_non_lzx_extraction_manifest(tmp_path: Path):
    root = tmp_path / "extracted"
    _write_extracted_entry(root)

    failed_manifest = tmp_path / "failed.csv"
    _write_manifest(failed_manifest, [_manifest_row(status="error")])
    with pytest.raises(ValueError, match="status is not ok"):
        MODULE.resolve_extracted_entry(root, failed_manifest, _identity())

    wrong_method_manifest = tmp_path / "wrong-method.csv"
    _write_manifest(wrong_method_manifest, [_manifest_row(method="zlib")])
    with pytest.raises(ValueError, match="not XMem/LZX"):
        MODULE.resolve_extracted_entry(root, wrong_method_manifest, _identity())


def test_extraction_adapter_delegates_final_hash_and_rate_admission_to_canonical_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "extracted"
    decoded_path = _write_extracted_entry(
        root, b'<root><prop name="tick rate" data="360" /></root>'
    )
    manifest = tmp_path / "_bff_manifest.csv"
    _write_manifest(manifest, [_manifest_row()])

    monkeypatch.setattr(MODULE, "_resource_identity", lambda _path: _identity())
    calls: list[Path] = []

    def fake_materialize(
        _geometry: Path,
        _cadence: Path,
        *,
        decoded_entry_path: Path | None = None,
        archive_path: Path | None = None,
    ) -> dict:
        assert archive_path is None
        assert decoded_entry_path == decoded_path
        calls.append(decoded_entry_path)
        return {
            "format": "SHIFT.SelectedSessionPhysicsTweakerRate/1",
            "ready": True,
            "status": "selected-session-physics-tweaker-rate-ready",
            "verification": {
                "mode": "exact-decoded-entry",
                "archive_sha256_verified_this_run": False,
                "decoded_sha256_verified_this_run": True,
            },
            "selected_session_rate": {"rate_hz": 360},
        }

    monkeypatch.setattr(MODULE, "materialize", fake_materialize)
    report = MODULE.materialize_from_extraction(
        tmp_path / "geometry.json",
        tmp_path / "cadence.json",
        root,
        manifest,
    )

    assert calls == [decoded_path]
    verification = report["verification"]
    assert verification["mode"] == "exact-extracted-entry-manifest"
    assert verification["decoded_sha256_verified_this_run"] is True
    assert verification["archive_sha256_verified_this_run"] is False
    assert verification["extraction_manifest_verified_this_run"] is True
    assert verification["extraction_manifest_entry"]["entry_index"] == 49
    assert verification["extraction_manifest_entry"]["crc_field"] == "0xa0f8c093"


def test_adapter_source_cannot_promote_manifest_metadata_without_decoded_hash():
    source = TOOL.read_text(encoding="utf-8")
    assert "decoded XML bytes still have to pass the canonical hash" in source
    assert "materialize(" in source
    assert "decoded_entry_path=decoded_path" in source
    assert "rate_hz = 180" not in source
    assert "rate_hz = 360" not in source

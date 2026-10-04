from __future__ import annotations

from pathlib import Path

from native_scene_external_sampler_capture import _resolve_snapshot_path


def _ppm(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"P6\n1 1\n255\n" + bytes((1, 2, 3)))


def test_windows_capture_path_relocates_by_exact_launcher_layout(tmp_path: Path):
    ppm = tmp_path / "textures" / "shift_d3d9_s7_0x1234.ppm"
    _ppm(ppm)

    resolved, mode, blockers = _resolve_snapshot_path(
        r"C:\capture\textures\shift_d3d9_s7_0x1234.ppm",
        tmp_path,
    )

    assert resolved == ppm.resolve()
    assert mode == "capture-launcher-textures-relative"
    assert blockers == []


def test_posix_capture_path_relocates_by_exact_launcher_layout(tmp_path: Path):
    ppm = tmp_path / "textures" / "shift_d3d9_s3_0x99_face_px.ppm"
    _ppm(ppm)

    resolved, mode, blockers = _resolve_snapshot_path(
        "/old/capture/textures/shift_d3d9_s3_0x99_face_px.ppm",
        tmp_path,
    )

    assert resolved == ppm.resolve()
    assert mode == "capture-launcher-textures-relative"
    assert blockers == []


def test_unique_basename_outside_launcher_layout_is_not_identity_proof(tmp_path: Path):
    only_hit = tmp_path / "copied" / "shift_d3d9_s7_0x1234.ppm"
    _ppm(only_hit)

    resolved, mode, blockers = _resolve_snapshot_path(
        r"C:\capture\snapshots\shift_d3d9_s7_0x1234.ppm",
        tmp_path,
    )

    assert resolved is None
    assert mode == "unresolved"
    assert blockers == ["snapshot-path-no-exact-relocation"]


def test_relative_snapshot_path_must_exist_at_exact_capture_root_location(tmp_path: Path):
    _ppm(tmp_path / "other" / "shadow.ppm")

    resolved, mode, blockers = _resolve_snapshot_path(
        "textures/shadow.ppm",
        tmp_path,
    )

    assert resolved is None
    assert mode == "unresolved"
    assert blockers == ["snapshot-path-not-found"]


def test_relative_snapshot_path_cannot_escape_capture_root(tmp_path: Path):
    outside = tmp_path.parent / "outside.ppm"
    _ppm(outside)

    resolved, mode, blockers = _resolve_snapshot_path(
        "../outside.ppm",
        tmp_path,
    )

    assert resolved is None
    assert mode == "unresolved"
    assert blockers == ["snapshot-path-escapes-capture-root"]

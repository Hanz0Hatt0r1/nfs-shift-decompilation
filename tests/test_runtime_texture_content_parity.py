from pathlib import Path

import runtime_texture_content_parity as parity


def _image(rgb, width=2, height=1):
    pixels = []
    for pixel in rgb:
        pixels.extend([*pixel, 255])
    return {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "synthetic",
        "width": width,
        "height": height,
        "pixels": pixels,
    }


def _ppm(path: Path, rgb):
    path.write_bytes(
        f"P6\n2 1\n255\n".encode("ascii") + bytes(sum(([r, g, b] for r, g, b in rgb), []))
    )


def test_compare_snapshot_to_expected_matches_exact_rgb(tmp_path):
    expected = _image([(10, 20, 30), (40, 50, 60)])
    path = tmp_path / "snapshot.ppm"
    _ppm(path, [(10, 20, 30), (40, 50, 60)])
    expected = {
        "width": 2,
        "height": 1,
        "decoded_rgb_sha256": parity._rgb_sha256(expected),
    }
    report = parity.compare_snapshot_to_expected(path, expected)
    assert report["ready"] is True
    assert report["status"] == "match"
    assert report["alpha_status"] == "not-observed"


def test_compare_snapshot_to_expected_rejects_rgb_mismatch(tmp_path):
    expected_image = _image([(10, 20, 30), (40, 50, 60)])
    path = tmp_path / "snapshot.ppm"
    _ppm(path, [(10, 20, 31), (40, 50, 60)])
    expected = {
        "width": 2,
        "height": 1,
        "decoded_rgb_sha256": parity._rgb_sha256(expected_image),
    }
    report = parity.compare_snapshot_to_expected(path, expected)
    assert report["ready"] is False
    assert "snapshot:rgb-content-mismatch" in report["blocking_reasons"][0]


def test_compare_snapshot_to_expected_rejects_dimension_mismatch(tmp_path):
    expected_image = _image([(10, 20, 30), (40, 50, 60)])
    path = tmp_path / "snapshot.ppm"
    path.write_bytes(b"P6\n1 1\n255\n\x01\x02\x03")
    expected = {
        "width": 2,
        "height": 1,
        "decoded_rgb_sha256": parity._rgb_sha256(expected_image),
    }
    report = parity.compare_snapshot_to_expected(path, expected)
    assert report["ready"] is False
    assert any(reason.startswith("snapshot:dimensions-mismatch") for reason in report["blocking_reasons"])


def test_bmw_paint_parity_requires_snapshot_for_all_material_textures(monkeypatch):
    snapshot = {
        "frame": 9,
        "draw_snapshots": [{
            "draw_index": 3,
            "active_texture_bindings": [
                {"stage": 1, "texture_ptr": "0x100", "snapshot_paths": []},
                {"stage": 2, "texture_ptr": "0x200", "snapshot_paths": []},
                {"stage": 4, "texture_ptr": "0x400", "snapshot_paths": []},
            ],
        }],
    }
    expected = {
        "diffuseTexture": {"parameter": "diffuseTexture", "register": 1, "path": "a", "archive": "b", "entry_index": 1, "source_sha256": "a", "source_size": 1, "width": 1, "height": 1, "decoded_rgba_sha256": "a", "decoded_rgb_sha256": "a", "decoded_alpha_observable": True},
        "specularTexture": {"parameter": "specularTexture", "register": 2, "path": "b", "archive": "b", "entry_index": 2, "source_sha256": "b", "source_size": 1, "width": 1, "height": 1, "decoded_rgba_sha256": "b", "decoded_rgb_sha256": "b", "decoded_alpha_observable": True},
        "scratchControlTexture": {"parameter": "scratchControlTexture", "register": 4, "path": "c", "archive": "b", "entry_index": 3, "source_sha256": "c", "source_size": 1, "width": 1, "height": 1, "decoded_rgba_sha256": "c", "decoded_rgb_sha256": "c", "decoded_alpha_observable": True},
    }
    monkeypatch.setattr(parity, "_extract_expected_textures", lambda _bff: expected)
    report = parity.build_bmw_paint_runtime_texture_parity(
        snapshot,
        frame=9,
        draw_index=3,
        primary_bff="BMW_M3_E36.bff",
    )
    assert report["ready"] is False
    assert report["matched_texture_count"] == 0
    assert set(report["blocking_reasons"]) == {
        "runtime:texture-snapshot-not-supplied:s1",
        "runtime:texture-snapshot-not-supplied:s2",
        "runtime:texture-snapshot-not-supplied:s4",
    }


def test_pipeline_snapshot_inventory_reads_snapshot_paths():
    from bmw_runtime_capture_pipeline import _texture_snapshot_inventory

    assert _texture_snapshot_inventory({
        "frames": [{
            "frame": 1,
            "texture_bindings": [{"stage": 1, "texture_ptr": "0x1", "snapshot_paths": []}],
        }]
    }) == {
        "capture_snapshot_count": 0,
        "converted_snapshot_count": 0,
        "snapshots": [],
    }


def test_bmw_paint_parity_rejects_multiple_snapshot_paths(monkeypatch):
    snapshot = {
        "frames": [{
            "frame": 9,
            "draw_snapshots": [{
                "draw_index": 3,
                "active_texture_bindings": [
                    {"stage": 1, "texture_ptr": "0x100", "snapshot_paths": ["a.ppm", "b.ppm"]},
                    {"stage": 2, "texture_ptr": "0x200", "snapshot_paths": []},
                    {"stage": 4, "texture_ptr": "0x400", "snapshot_paths": []},
                ],
            }],
        }],
    }
    expected = {
        key: {
            "parameter": key, "register": register, "path": key,
            "archive": "b", "entry_index": register, "source_sha256": "a",
            "source_size": 1, "width": 1, "height": 1, "decoded_rgba_sha256": "a",
            "decoded_rgb_sha256": "a", "decoded_alpha_observable": True,
        }
        for key, register in (
            ("diffuseTexture", 1), ("specularTexture", 2), ("scratchControlTexture", 4)
        )
    }
    monkeypatch.setattr(parity, "_extract_expected_textures", lambda _bff: expected)
    report = parity.build_bmw_paint_runtime_texture_parity(
        snapshot, frame=9, draw_index=3, primary_bff="BMW_M3_E36.bff"
    )
    assert report["ready"] is False
    assert "runtime:texture-snapshot-ambiguous:s1" in report["blocking_reasons"]

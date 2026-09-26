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




def _dds_for_test(payload):
    header = bytearray(128)
    header[0:4] = b"DDS "
    header[12:16] = (4).to_bytes(4, "little")
    header[16:20] = (4).to_bytes(4, "little")
    header[84:88] = int.from_bytes(b"DXT1", "little").to_bytes(4, "little")
    return bytes(header) + bytes(payload)

def _dds_dxt1(width, height, base_payload):
    header = bytearray(128)
    header[0:4] = b"DDS "
    header[12:16] = int(height).to_bytes(4, "little")
    header[16:20] = int(width).to_bytes(4, "little")
    header[84:88] = int.from_bytes(b"DXT1", "little").to_bytes(4, "little")
    return bytes(header) + bytes(base_payload)


def test_compare_raw_payload_to_dds_base_level_exact(tmp_path):
    payload = b"01234567"
    dds = _dds_dxt1(4, 4, payload)
    raw = tmp_path / "texture.bin"
    raw.write_bytes(payload)
    report = parity.compare_raw_payload_to_dds(raw, dds)
    assert report["ready"] is True
    assert report["status"] == "match"
    assert report["dds_source_format"] == "DXT1"


def test_compare_raw_payload_to_dds_rejects_length_and_content_mismatch(tmp_path):
    dds = _dds_dxt1(4, 4, b"01234567")
    raw = tmp_path / "texture.bin"
    raw.write_bytes(b"012345")
    report = parity.compare_raw_payload_to_dds(raw, dds)
    assert report["ready"] is False
    assert any(reason.startswith("raw-payload:length-mismatch") for reason in report["blocking_reasons"])
    assert any(reason.startswith("raw-payload:sha256-mismatch") for reason in report["blocking_reasons"])


def test_texture_payload_candidates_are_ordered_by_event_index():
    rows = parity._texture_payload_candidates({
        "texture_payloads": [
            {"texture_ptr": "0x100", "level": 0, "snapshot_status": "captured", "payload_path": "late.bin", "event_index": 20},
            {"texture_ptr": "0x100", "level": 1, "snapshot_status": "captured", "payload_path": "mip.bin", "event_index": 30},
            {"texture_ptr": "0x100", "level": 0, "snapshot_status": "captured", "payload_path": "early.bin", "event_index": 10},
        ],
    }, "0x100")
    assert [row["payload_path"] for row in rows] == ["early.bin", "late.bin"]


def test_texture_payload_candidates_ignore_payload_from_previous_pointer_lifetime():
    rows = parity._texture_payload_candidates({
        "texture_payloads": [
            {"texture_ptr": "0x100", "level": 0, "snapshot_status": "captured", "payload_path": "old.bin", "event_index": 10},
            {"texture_ptr": "0x100", "level": 0, "snapshot_status": "captured", "payload_path": "current.bin", "event_index": 30},
        ],
    }, "0x100", creation_event_index=20)
    assert [row["payload_path"] for row in rows] == ["current.bin"]


def test_bmw_paint_parity_accepts_raw_payload_without_ppm(tmp_path, monkeypatch):
    tokens = {
        "diffuseTexture": b"ABCDEFGH",
        "specularTexture": b"IJKLMNOP",
        "scratchControlTexture": b"QRSTUVWX",
    }
    expected = {}
    for parameter, register in (
        ("diffuseTexture", 1),
        ("specularTexture", 2),
        ("scratchControlTexture", 4),
    ):
        expected[parameter] = {
            "parameter": parameter,
            "register": register,
            "path": f"{parameter}.dds",
            "archive": "BMW_M3_E36.bff",
            "entry_index": register,
            "source_sha256": "x" * 64,
            "source_size": 136,
            "width": 4,
            "height": 4,
            "mipmaps": 1,
            "fourcc": "DXT1",
            "decoded_rgba_sha256": "r" * 64,
            "decoded_rgb_sha256": "g" * 64,
            "decoded_alpha_observable": True,
        }

    def fake_dds(_bff):
        return {parameter: _dds_for_test(token) for parameter, token in tokens.items()}

    monkeypatch.setattr(parity, "_extract_expected_textures", lambda _bff: expected)
    monkeypatch.setattr(parity, "_extract_expected_texture_payloads", fake_dds)

    paths = {}
    for parameter, token in tokens.items():
        path = tmp_path / f"{parameter}.bin"
        path.write_bytes(token)
        paths[parameter] = path

    snapshot = {
        "frames": [{
            "frame": 9,
            "draw_snapshots": [{
                "draw_index": 3,
                "active_texture_bindings": [
                    {
                        "stage": 1, "texture_ptr": "0x100",
                        "snapshot_paths": [],
                        "resource_creation": {"event_index": 10},
                    },
                    {
                        "stage": 2, "texture_ptr": "0x200",
                        "snapshot_paths": [],
                        "resource_creation": {"event_index": 20},
                    },
                    {
                        "stage": 4, "texture_ptr": "0x400",
                        "snapshot_paths": [],
                        "resource_creation": {"event_index": 30},
                    },
                ],
                "texture_payloads": [
                    {"texture_ptr": "0x100", "level": 0, "snapshot_status": "captured", "payload_path": str(paths["diffuseTexture"]), "event_index": 11},
                    {"texture_ptr": "0x200", "level": 0, "snapshot_status": "captured", "payload_path": str(paths["specularTexture"]), "event_index": 21},
                    {"texture_ptr": "0x400", "level": 0, "snapshot_status": "captured", "payload_path": str(paths["scratchControlTexture"]), "event_index": 31},
                ],
            }],
        }],
    }

    report = parity.build_bmw_paint_runtime_texture_parity(
        snapshot, frame=9, draw_index=3, primary_bff="BMW_M3_E36.bff"
    )
    assert report["ready"] is True
    assert report["matched_texture_count"] == 3
    assert all(row["content_identity_method"] == "raw-dds-base-level" for row in report["textures"])


def _dds_dxt1_chain(width, height, levels):
    header = bytearray(128)
    header[0:4] = b"DDS "
    header[12:16] = int(height).to_bytes(4, "little")
    header[16:20] = int(width).to_bytes(4, "little")
    header[28:32] = int(len(levels)).to_bytes(4, "little")
    header[84:88] = int.from_bytes(b"DXT1", "little").to_bytes(4, "little")
    return bytes(header) + b"".join(levels)


def test_compare_raw_payload_chain_is_complete_when_all_mips_match(tmp_path):
    levels = [b"ABCDEFGH", b"IJKLMNOP", b"QRSTUVWX"]
    dds = _dds_dxt1_chain(4, 4, levels)
    rows = []
    for level, payload in enumerate(levels):
        path = tmp_path / f"l{level}.bin"
        path.write_bytes(payload)
        rows.append({
            "level": level,
            "event_index": level + 2,
            "snapshot_status": "captured",
            "payload_path": str(path),
        })
    report = parity.compare_raw_payload_chain_to_dds(rows, dds)
    assert report["ready"] is True
    assert report["coverage_status"] == "complete"
    assert report["observed_levels"] == [0, 1, 2]
    assert report["missing_levels"] == []
    assert all(item["status"] == "match" for item in report["levels"])


def test_compare_raw_payload_chain_is_partial_when_higher_mips_are_missing(tmp_path):
    levels = [b"ABCDEFGH", b"IJKLMNOP", b"QRSTUVWX"]
    dds = _dds_dxt1_chain(4, 4, levels)
    path = tmp_path / "l0.bin"
    path.write_bytes(levels[0])
    report = parity.compare_raw_payload_chain_to_dds([{
        "level": 0,
        "event_index": 2,
        "snapshot_status": "captured",
        "payload_path": str(path),
    }], dds)
    assert report["ready"] is True
    assert report["coverage_status"] == "partial"
    assert report["observed_levels"] == [0]
    assert report["missing_levels"] == [1, 2]


def test_compare_raw_payload_chain_blocks_on_any_captured_mip_mismatch(tmp_path):
    levels = [b"ABCDEFGH", b"IJKLMNOP", b"QRSTUVWX"]
    dds = _dds_dxt1_chain(4, 4, levels)
    paths = []
    for level, payload in enumerate((levels[0], b"BADBYTES", levels[2])):
        path = tmp_path / f"l{level}.bin"
        path.write_bytes(payload)
        paths.append(path)
    rows = [
        {
            "level": level,
            "event_index": level + 2,
            "snapshot_status": "captured",
            "payload_path": str(path),
        }
        for level, path in enumerate(paths)
    ]
    report = parity.compare_raw_payload_chain_to_dds(rows, dds)
    assert report["ready"] is False
    assert report["coverage_status"] == "complete"
    assert any(reason.startswith("raw-payload:sha256-mismatch:l1") for reason in report["blocking_reasons"])


def test_runtime_global_payloads_are_used_when_draw_snapshot_is_from_later_frame(tmp_path):
    path = tmp_path / "l0.bin"
    path.write_bytes(b"ABCDEFGH")
    snapshot = {
        "draw": {"event_index": 50},
        "texture_payloads": [],
    }
    runtime_report = {
        "texture_payloads": [{
            "texture_ptr": "0x100",
            "level": 0,
            "event_index": 20,
            "snapshot_status": "captured",
            "payload_path": str(path),
        }],
    }
    rows = parity._runtime_texture_payload_candidates(
        runtime_report, snapshot, "0x100", creation_event_index=10, draw_event_index=50
    )
    assert len(rows) == 1
    assert rows[0]["payload_path"] == str(path)


def test_runtime_global_payloads_ignore_payload_after_draw(tmp_path):
    path = tmp_path / "late.bin"
    path.write_bytes(b"ABCDEFGH")
    rows = parity._runtime_texture_payload_candidates(
        {
            "texture_payloads": [{
                "texture_ptr": "0x100",
                "level": 0,
                "event_index": 60,
                "snapshot_status": "captured",
                "payload_path": str(path),
            }]
        },
        {"draw": {"event_index": 50}, "texture_payloads": []},
        "0x100",
        creation_event_index=10,
        draw_event_index=50,
    )
    assert rows == []

from ppm_svg_snapshot import ppm_to_svg, read_ppm


def test_read_ppm_and_make_compact_svg(tmp_path):
    ppm = tmp_path / "frame.ppm"
    ppm.write_bytes(
        b"P6\n4 2\n255\n"
        + bytes([
            255, 0, 0,   0, 255, 0,   0, 0, 255,   255, 255, 0,
            10, 20, 30,  40, 50, 60,  70, 80, 90,  100, 110, 120,
        ])
    )
    width, height, pixels = read_ppm(ppm)
    assert (width, height) == (4, 2)
    assert pixels[:3] == bytes((255, 0, 0))

    svg = tmp_path / "frame.svg"
    report = ppm_to_svg(ppm, svg, max_width=2, max_height=2)
    assert report["format"] == "SHIFT.PPMSnapshotSVG/1"
    assert report["source_width"] == 4
    assert report["source_height"] == 2
    assert report["snapshot_width"] == 2
    assert report["snapshot_height"] == 1
    text = svg.read_text(encoding="utf-8")
    assert 'viewBox="0 0 2 1"' in text
    assert text.count("<rect ") == 2


def test_read_ppm_rejects_wrong_payload_size(tmp_path):
    ppm = tmp_path / "bad.ppm"
    ppm.write_bytes(b"P6\n2 2\n255\n" + bytes((1, 2, 3)))
    try:
        read_ppm(ppm)
    except ValueError as exc:
        assert "payload size mismatch" in str(exc)
    else:
        raise AssertionError("expected payload size mismatch")

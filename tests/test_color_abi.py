import pytest

from color_abi import (
    build_color_abi_evidence,
    compare_color_candidate,
    interpret_color_bytes,
)


def test_color_abi_preserves_rgba_and_bgra_candidates():
    raw = bytes((10, 20, 30, 40, 100, 110, 120, 130))
    result = build_color_abi_evidence("460", raw)
    assert result["format"] == "SHIFT.ColorABIEvidence/1"
    assert result["property_id"] == "460"
    assert result["confidence"] == "ambiguous-channel-order"
    by_order = {x["order"]: x for x in result["candidates"]}
    assert interpret_color_bytes(raw, "RGBA") == raw
    assert interpret_color_bytes(raw, "BGRA") == bytes((30, 20, 10, 40, 120, 110, 100, 130))
    assert by_order["RGBA"]["stats"]["samples"] == 2
    assert by_order["RGBA"]["stats"]["alpha_non_opaque"] == 2


def test_color_abi_known_reference_can_distinguish_candidates_without_selection():
    raw = bytes((10, 20, 30, 255))
    expected = bytes((30, 20, 10, 255))
    result = compare_color_candidate("461", raw, expected)
    assert result["format"] == "SHIFT.ColorABICandidateComparison/1"
    assert result["selection"] == "not-selected"
    matches = {x["order"]: x for x in result["candidate_results"]}
    assert matches["RGBA"]["exact_match"] is False
    assert matches["BGRA"]["exact_match"] is True


def test_color_abi_rejects_unknown_property():
    with pytest.raises(ValueError, match="unsupported color property"):
        build_color_abi_evidence("200", b"\x00\x00\x00\x00")


def test_color_abi_rejects_partial_sample():
    with pytest.raises(ValueError, match="divisible by four"):
        build_color_abi_evidence("460", b"\x01\x02\x03")


def test_color_abi_cli_writes_non_selecting_evidence_report(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    raw = tmp_path / "color.bin"
    expected = tmp_path / "expected.rgba"
    output = tmp_path / "evidence.json"
    raw.write_bytes(bytes((10, 20, 30, 255, 40, 50, 60, 255)))
    expected.write_bytes(bytes((30, 20, 10, 255, 60, 50, 40, 255)))

    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "shift_importer.py"),
            "color-evidence",
            "460",
            str(raw),
            str(output),
            "--expected-rgba",
            str(expected),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["format"] == "SHIFT.ColorABIEvidence/1"
    assert result["confidence"] == "ambiguous-channel-order"
    assert result["comparison"]["selection"] == "not-selected"
    matches = {row["order"]: row for row in result["comparison"]["candidate_results"]}
    assert matches["BGRA"]["exact_match"] is True
    assert matches["RGBA"]["exact_match"] is False


def test_color_abi_cli_rejects_non_color_property(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    raw = tmp_path / "color.bin"
    output = tmp_path / "evidence.json"
    raw.write_bytes(b"\\x00\\x00\\x00\\x00")

    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "shift_importer.py"),
            "color-evidence",
            "200",
            str(raw),
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert not output.exists()


def test_color_abi_cli_reads_mgeo_style_json_color_stream(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    mesh = tmp_path / "mesh.json"
    output = tmp_path / "evidence.json"
    mesh.write_text(
        json.dumps({
            "format": "SHIFT.MEB",
            "vertex_count": 2,
            "colors": [[10, 20, 30, 255], [40, 50, 60, 255]],
            "colors2": [[70, 80, 90, 255], [100, 110, 120, 255]],
        }),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "shift_importer.py"),
            "color-evidence",
            "460",
            str(mesh),
            str(output),
            "--mesh-json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["source"]["kind"] == "meb-json"
    assert result["source"]["stream"] == "colors"
    assert result["source"]["vertex_count"] == 2
    assert result["sample_count"] == 2
    rgba = next(x for x in result["candidates"] if x["order"] == "RGBA")
    assert rgba["rgba8_hex"] == "0a141eff28323cff"


def test_color_abi_cli_reads_property_461_from_colors2(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    mesh = tmp_path / "mesh.json"
    output = tmp_path / "evidence.json"
    mesh.write_text(
        json.dumps({
            "colors2": [[1, 2, 3, 4]],
        }),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "shift_importer.py"),
            "color-evidence",
            "461",
            str(mesh),
            str(output),
            "--mesh-json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["source"]["stream"] == "colors2"
    assert result["candidates"][0]["rgba8_hex"] in {"01020304", "03020104"}

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


def test_color_evidence_resource_reads_mab_from_bff(monkeypatch, tmp_path):
    import argparse
    import json
    from types import SimpleNamespace

    import shift_importer

    mesh = SimpleNamespace(
        colors=[(10, 20, 30, 255), (40, 50, 60, 255)],
        colors2=[],
        vertex_count=2,
        property_layouts=[{"id": "460", "payload_offset": 64, "stride": 4, "bytes": 8}],
    )
    entry = SimpleNamespace(index=7, path="cars/body.meb")
    fake_bff = SimpleNamespace(
        path=SimpleNamespace(name="CARS.bff"),
        entries=[entry],
    )
    fake_bff.extract_entry = lambda _entry, type2="lzx": b"decoded-meb"
    output = tmp_path / "resource-color.json"

    class FakeBFF:
        def __init__(self, _path):
            self.inner = fake_bff
            self.path = fake_bff.path
            self.entries = fake_bff.entries

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_entry(self, entry_arg, type2="lzx"):
            return self.inner.extract_entry(entry_arg, type2=type2)

    monkeypatch.setattr(shift_importer, "BFF", FakeBFF)
    monkeypatch.setattr(shift_importer, "read_meb", lambda _data: mesh)
    monkeypatch.setattr(shift_importer, "sha256", lambda _data: "meb-sha256")

    args = argparse.Namespace(
        archive="CARS.bff",
        resource="cars/body.meb",
        property_id="460",
        output=str(output),
        expected_rgba=None,
    )
    assert shift_importer.cmd_color_evidence_resource(args) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["format"] == "SHIFT.ColorABIEvidence/1"
    assert report["source"]["kind"] == "bff-meb"
    assert report["source"]["archive"] == "CARS.bff"
    assert report["source"]["entry_index"] == 7
    assert report["source"]["stream"] == "colors"
    assert report["source"]["property_layout"]["payload_offset"] == 64
    assert report["sample_count"] == 2


def test_color_evidence_resource_uses_colors2_for_property_461(monkeypatch, tmp_path):
    import argparse
    import json
    from types import SimpleNamespace

    import shift_importer

    mesh = SimpleNamespace(
        colors=[],
        colors2=[(1, 2, 3, 255)],
        vertex_count=1,
        property_layouts=[{"id": "461", "payload_offset": 128, "stride": 4, "bytes": 4}],
    )
    entry = SimpleNamespace(index=9, path="cars/body.meb")

    class FakeBFF:
        path = SimpleNamespace(name="CARS.bff")
        entries = [entry]

        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_entry(self, _entry, type2="lzx"):
            return b"decoded-meb"

    output = tmp_path / "resource-color2.json"
    monkeypatch.setattr(shift_importer, "BFF", FakeBFF)
    monkeypatch.setattr(shift_importer, "read_meb", lambda _data: mesh)
    monkeypatch.setattr(shift_importer, "sha256", lambda _data: "meb-sha256")

    args = argparse.Namespace(
        archive="CARS.bff",
        resource="cars/body.meb",
        property_id="461",
        output=str(output),
        expected_rgba=None,
    )
    assert shift_importer.cmd_color_evidence_resource(args) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["source"]["stream"] == "colors2"
    assert report["source"]["vertex_count"] == 1
    assert report["candidates"][0]["rgba8_hex"] == "010203ff"



def test_color_abi_corpus_aggregates_multiple_reports_without_selection():
    from color_abi import aggregate_color_abi_evidence, build_color_abi_evidence

    first = build_color_abi_evidence(
        "460",
        bytes((10, 20, 30, 255, 40, 50, 60, 255)),
    )
    second = build_color_abi_evidence(
        "460",
        bytes((70, 80, 90, 255, 100, 110, 120, 255)),
    )
    first_461 = build_color_abi_evidence(
        "461",
        bytes((1, 2, 3, 4)),
    )

    report = aggregate_color_abi_evidence([first, second, first_461])
    assert report["format"] == "SHIFT.ColorABICorpusEvidence/1"
    assert report["report_count"] == 3
    assert report["selection"] == "not-selected"
    assert report["properties"]["460"]["report_count"] == 2
    assert report["properties"]["460"]["selection"] == "not-selected"
    assert report["properties"]["461"]["report_count"] == 1
    orders = {
        row["order"]: row
        for row in report["properties"]["460"]["candidate_consistency"]
    }
    assert orders["RGBA"]["reports"] == 2
    assert orders["RGBA"]["stable_across_reports"] is False


def test_color_abi_corpus_marks_invalid_reports():
    from color_abi import aggregate_color_abi_evidence

    report = aggregate_color_abi_evidence([
        {"format": "SHIFT.NotColor/1", "property_id": "460"},
        {"format": "SHIFT.ColorABIEvidence/1", "property_id": "200"},
    ])
    assert report["report_count"] == 2
    assert len(report["invalid_reports"]) == 2
    assert report["selection"] == "not-selected"



def test_color_abi_corpus_cli_aggregates_directory(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    from color_abi import build_color_abi_evidence

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "a.json").write_text(
        json.dumps(build_color_abi_evidence("460", bytes((1, 2, 3, 255)))),
        encoding="utf-8",
    )
    (evidence_dir / "b.json").write_text(
        json.dumps(build_color_abi_evidence("461", bytes((4, 5, 6, 255)))),
        encoding="utf-8",
    )
    (evidence_dir / "ignored.json").write_text(
        json.dumps({"format": "SHIFT.Other/1"}),
        encoding="utf-8",
    )
    output = tmp_path / "corpus.json"

    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "shift_importer.py"),
            "color-evidence-corpus",
            str(evidence_dir),
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["format"] == "SHIFT.ColorABICorpusEvidence/1"
    assert report["report_count"] == 2
    assert report["source"]["accepted_reports"] == 2
    assert report["properties"]["460"]["report_count"] == 1
    assert report["properties"]["461"]["report_count"] == 1
    assert report["selection"] == "not-selected"


def test_color_evidence_bff_corpus_scans_meb_color_streams(monkeypatch, tmp_path):
    import argparse
    import json
    from types import SimpleNamespace

    import shift_importer

    entry = SimpleNamespace(index=3, path="cars/bmw/body.meb")
    mesh = SimpleNamespace(
        colors=[(10, 20, 30, 255)],
        colors2=[(40, 50, 60, 255)],
        vertex_count=1,
    )

    class FakeBFF:
        path = SimpleNamespace(name="CARS.bff")
        entries = [entry]

        def __init__(self, path):
            self.archive = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_entry(self, _entry, type2="lzx"):
            return b"meb-bytes"

    monkeypatch.setattr(
        shift_importer,
        "iter_bffs",
        lambda _path: [tmp_path / "CARS.bff"],
    )
    monkeypatch.setattr(shift_importer, "BFF", FakeBFF)
    monkeypatch.setattr(shift_importer, "read_meb", lambda _data: mesh)
    monkeypatch.setattr(shift_importer, "sha256", lambda _data: "sha")

    output = tmp_path / "corpus.json"
    args = argparse.Namespace(
        input=str(tmp_path),
        output=str(output),
        fail_on_error=False,
    )
    assert shift_importer.cmd_color_evidence_bff_corpus(args) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["format"] == "SHIFT.ColorABICorpusEvidence/1"
    assert report["source"]["accepted_reports"] == 2
    assert report["source"]["resource_count"] == 2
    assert report["source"]["errors"] == []
    assert report["properties"]["460"]["report_count"] == 1
    assert report["properties"]["461"]["report_count"] == 1
    assert report["selection"] == "not-selected"


def test_color_evidence_bff_corpus_can_fail_on_decode_error(monkeypatch, tmp_path):
    import argparse
    from types import SimpleNamespace

    import shift_importer

    entry = SimpleNamespace(index=4, path="bad/body.meb")
    class FakeBFF:
        path = SimpleNamespace(name="BAD.bff")
        entries = [entry]

        def __init__(self, path):
            self.archive = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_entry(self, _entry, type2="lzx"):
            raise ValueError("decode failed")

    monkeypatch.setattr(shift_importer, "iter_bffs", lambda _path: [tmp_path / "BAD.bff"])
    monkeypatch.setattr(shift_importer, "BFF", FakeBFF)

    output = tmp_path / "errors.json"
    args = argparse.Namespace(
        input=str(tmp_path),
        output=str(output),
        fail_on_error=True,
    )
    assert shift_importer.cmd_color_evidence_bff_corpus(args) == 1


def test_color_abi_exposes_d3d9_declaration_candidates():
    from color_abi import interpret_color_d3d9

    raw = bytes((0x12, 0x34, 0x56, 0x78))
    result = build_color_abi_evidence("460", raw)
    assert result["confidence"] == "ambiguous-declaration-and-channel-order"
    by_order = {row["order"]: row for row in result["candidates"]}
    assert by_order["RGBA"]["d3d9_type"] == "UBYTE4N"
    assert by_order["RGBA"]["memory_order"] == "RGBA"
    assert by_order["BGRA"]["d3d9_type"] == "D3DCOLOR"
    assert by_order["BGRA"]["memory_order"] == "BGRA"
    assert by_order["BGRA"]["shader_order"] == "RGBA"
    assert interpret_color_d3d9(raw, "UBYTE4N") == raw
    assert interpret_color_d3d9(raw, "D3DCOLOR") == bytes((0x56, 0x34, 0x12, 0x78))
    assert result["source_evidence"]["function"] == "FUN_008310c0"
    assert result["source_evidence"]["status"] == "supporting-packed-color-evidence-not-MEB-declaration-proof"


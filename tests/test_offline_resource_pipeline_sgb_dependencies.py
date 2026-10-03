from __future__ import annotations

from pathlib import Path

import offline_resource_pipeline as pipeline


class FakeEntry:
    def __init__(self, index: int, path: str, payload: bytes):
        self.index = index
        self.path = path
        self.offset = 0x3000 + index * 0x40
        self.type = 0
        self.compressed_size = len(payload)
        self.uncompressed_size = len(payload)
        self.crc32_field = 0xC000 + index
        self.fileext = 0
        self._payload = payload


class FakeBFF:
    entries_by_name: dict[str, list[FakeEntry]] = {}

    def __init__(self, path):
        self.path = Path(path)
        self.version = 3
        self.x12d = 0
        self.entries = list(self.entries_by_name[self.path.name])

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def extract_entry(self, entry, type2="lzx"):
        return entry._payload

    def raw_payload(self, entry):
        return entry._payload


def _materialized(path: Path) -> list[pipeline.MaterializedArchive]:
    return [pipeline.MaterializedArchive(str(path), None, path)]


def _scan_analysis():
    return {
        "path": "tracks/test/scene.sgb",
        "extension": ".sgb",
        "size": 16,
        "analysis": {
            "format": "SHIFT.SGB",
            "resource_refs": [
                {
                    "path": "tracks/test/diagnostic.dds",
                    "kind": "texture",
                    "confidence": "string-scan",
                }
            ],
        },
    }


def _runtime_report(*, ready: bool):
    return {
        "format": "SHIFT.SGBRuntime/1",
        "status": "decoded" if ready else "decoded-with-blockers",
        "ready": ready,
        "chunk_count": 2,
        "blockers": [] if ready else ["FLAT:decode:unsupported-fixture"],
        "chunks": [
            {
                "tag": "NODE",
                "decode_status": "decoded",
                "records": [
                    {
                        "index": 7,
                        "resource": {"text": "tracks/test/meshes/tree.imb"},
                    }
                ],
            },
            {
                "tag": "END ",
                "decode_status": "decoded",
            },
        ],
    }


def test_ready_sgb_runtime_record_field_becomes_exact_resolved_edge(monkeypatch, tmp_path):
    bff = tmp_path / "Track.bff"
    bff.write_bytes(b"fixture-archive")
    FakeBFF.entries_by_name = {
        "Track.bff": [
            FakeEntry(0, "tracks/test/scene.sgb", b"sgb-fixture"),
            FakeEntry(1, "tracks/test/meshes/tree.imb", b"mesh-fixture"),
        ]
    }
    monkeypatch.setattr(pipeline, "BFF", FakeBFF)
    monkeypatch.setattr(pipeline, "classify", lambda path: "TRACK")
    monkeypatch.setattr(pipeline, "analyze_decoded_resource", lambda path, payload: _scan_analysis())
    monkeypatch.setattr(pipeline, "parse_sgb_runtime", lambda payload, strict=False: _runtime_report(ready=True))

    catalog, graph, coverage = pipeline.build_catalog(
        _materialized(bff),
        decode_known=True,
        decode_limit_per_archive=1,
    )

    sgb = catalog["resources"][0]
    assert sgb["decode_status"] == "parsed"
    assert sgb["neutral_ir"]["format"] == "SHIFT.SGBRuntime/1"
    assert sgb["neutral_ir"]["ready"] is True
    assert sgb["neutral_ir"]["source_backed_resource_reference_count"] == 1
    assert sgb["neutral_ir"]["string_scan_reference_count"] == 1

    exact = [edge for edge in graph["edges"] if edge["admissible"]]
    diagnostic = [edge for edge in graph["edges"] if not edge["admissible"]]
    assert len(exact) == 1
    assert exact[0]["ref"] == "tracks/test/meshes/tree.imb"
    assert exact[0]["scope"] == "global-exact"
    assert exact[0]["parser"] == "sgb_runtime.parse_sgb_runtime"
    assert exact[0]["evidence"] == "source-backed-runtime-record-field"
    assert exact[0]["source_chunk"] == "NODE"
    assert exact[0]["source_record_index"] == 7
    assert exact[0]["source_field"] == "resource"
    assert exact[0]["status"] == "resolved"
    assert exact[0]["targets"] == [catalog["resources"][1]["id"]]

    assert len(diagnostic) == 1
    assert diagnostic[0]["ref"] == "tracks/test/diagnostic.dds"
    assert diagnostic[0]["status"] == "diagnostic"
    assert graph["boundary"]["sgb_string_scan_closes_dependencies"] is False
    assert graph["boundary"]["sgb_source_backed_record_fields_close_dependencies"] is True
    assert graph["boundary"]["sgb_source_backed_requires_runtime_decode_ready"] is True
    assert coverage["dependency_summary"]["blocking_admissible_edges"] == 0


def test_nonready_sgb_runtime_decode_blocks_resource_and_keeps_refs_diagnostic(
    monkeypatch,
    tmp_path,
):
    bff = tmp_path / "Track.bff"
    bff.write_bytes(b"fixture-archive")
    FakeBFF.entries_by_name = {
        "Track.bff": [
            FakeEntry(0, "tracks/test/scene.sgb", b"sgb-fixture"),
            FakeEntry(1, "tracks/test/meshes/tree.imb", b"mesh-fixture"),
        ]
    }
    monkeypatch.setattr(pipeline, "BFF", FakeBFF)
    monkeypatch.setattr(pipeline, "classify", lambda path: "TRACK")
    monkeypatch.setattr(pipeline, "analyze_decoded_resource", lambda path, payload: _scan_analysis())
    monkeypatch.setattr(pipeline, "parse_sgb_runtime", lambda payload, strict=False: _runtime_report(ready=False))

    catalog, graph, coverage = pipeline.build_catalog(
        _materialized(bff),
        decode_known=True,
        decode_limit_per_archive=1,
    )

    sgb = catalog["resources"][0]
    assert sgb["decode_status"] == "blocked"
    assert sgb["analysis_error"].startswith("source-backed-sgb-runtime-not-ready:")
    assert sgb["neutral_ir"]["ready"] is False
    assert sgb["neutral_ir"]["blockers"] == ["FLAT:decode:unsupported-fixture"]
    assert all(not edge["admissible"] for edge in graph["edges"])
    assert all(edge["status"] == "diagnostic" for edge in graph["edges"])
    assert coverage["validation"]["blocked"] == 1
    assert coverage["validation"]["unclassified_blocked"] == 1
    assert coverage["ready"] is False

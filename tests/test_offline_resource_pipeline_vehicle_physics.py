from __future__ import annotations

from pathlib import Path

import offline_resource_pipeline as pipeline


class FakeEntry:
    def __init__(self, index: int, path: str, payload: bytes):
        self.index = index
        self.path = path
        self.offset = 0x2000 + index * 0x40
        self.type = 0
        self.compressed_size = len(payload)
        self.uncompressed_size = len(payload)
        self.crc32_field = 0xB000 + index
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


def test_vehicle_physics_extensions_are_catalog_supported():
    assert set(pipeline.VEHICLE_PHYSICS_EXTENSIONS) <= pipeline.KNOWN_DECODE_EXTENSIONS


def test_catalog_validates_cdf_with_existing_source_backed_parser(monkeypatch, tmp_path):
    bff = tmp_path / "Car.bff"
    bff.write_bytes(b"fixture-archive")
    FakeBFF.entries_by_name = {
        "Car.bff": [
            FakeEntry(0, "vehicles/physics/chassis/car.cdf", b"[GENERAL]\nMass=1000\n"),
        ],
    }
    monkeypatch.setattr(pipeline, "BFF", FakeBFF)
    monkeypatch.setattr(pipeline, "classify", lambda path: "VEHICLE_PHYSICS")
    monkeypatch.setattr(
        pipeline,
        "parse_cdf",
        lambda payload, strict=False: {
            "format": "SHIFT.VehicleCDFRuntime/1",
            "status": "parsed",
            "ready": True,
            "section_count": 1,
            "entry_count": 1,
            "unknown_entry_count": 0,
            "warnings": [],
        },
    )

    catalog, graph, coverage = pipeline.build_catalog(
        _materialized(bff),
        decode_known=True,
    )

    row = catalog["resources"][0]
    assert row["decode_status"] == "parsed"
    assert row["analysis_format"] == "SHIFT.VehicleCDFRuntime/1"
    assert row["neutral_ir"] == {
        "format": "SHIFT.VehicleCDFRuntime/1",
        "resource_type": "CDF",
        "status": "parsed",
        "ready": True,
        "warnings": [],
        "section_count": 1,
        "entry_count": 1,
        "unknown_entry_count": 0,
    }
    assert row["dependencies"] == []
    assert graph["edges"] == []
    assert graph["boundary"]["vehicle_physics_dependency_inference"] is False
    assert catalog["boundary"]["vehicle_physics_validation"] == "existing-source-backed-parsers"
    assert catalog["boundary"]["vehicle_physics_dependency_inference"] is False
    assert coverage["validation"]["supported"] == 1
    assert coverage["validation"]["verified"] == 1
    assert coverage["validation"]["unsupported"] == 0
    assert coverage["validation_boundary"]["vehicle_physics_dependency_inference"] is False


def test_catalog_blocks_nonready_physics_parser_without_guessing_failure_taxonomy(
    monkeypatch,
    tmp_path,
):
    bff = tmp_path / "Car.bff"
    bff.write_bytes(b"fixture-archive")
    FakeBFF.entries_by_name = {
        "Car.bff": [
            FakeEntry(0, "vehicles/physics/engines/car.edf", b"future-layout"),
        ],
    }
    monkeypatch.setattr(pipeline, "BFF", FakeBFF)
    monkeypatch.setattr(pipeline, "classify", lambda path: "VEHICLE_PHYSICS")
    monkeypatch.setattr(
        pipeline,
        "parse_engine_edf",
        lambda payload, strict=False: {
            "format": "SHIFT.EngineEDFRuntime/1",
            "status": "parsed-with-warnings",
            "ready": False,
            "entry_count": 1,
            "unknown_entry_count": 1,
            "rpm_torque": {"point_count": 0},
            "warnings": ["line:1:unparsed:future-layout"],
        },
    )

    catalog, graph, coverage = pipeline.build_catalog(
        _materialized(bff),
        decode_known=True,
    )

    row = catalog["resources"][0]
    assert row["decode_status"] == "blocked"
    assert row["analysis_format"] == "SHIFT.EngineEDFRuntime/1"
    assert row["analysis_error"].startswith("source-backed-parser-not-ready:")
    assert row["neutral_ir"]["resource_type"] == "EDF"
    assert row["neutral_ir"]["ready"] is False
    assert row["dependencies"] == []
    assert graph["edges"] == []

    validation = coverage["validation"]
    assert validation["supported"] == 1
    assert validation["verified"] == 0
    assert validation["blocked"] == 1
    assert validation["malformed"] == 0
    assert validation["unknown_version_layout"] == 0
    assert validation["unclassified_blocked"] == 1
    assert coverage["parser_failures"][0]["error"].startswith(
        "source-backed-parser-not-ready:"
    )

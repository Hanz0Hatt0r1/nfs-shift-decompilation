from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/ghidra_exporter_parity/scalar-use-0374"


def test_scalar_use_shared_export_matches_legacy_fallback() -> None:
    manifest = json.loads((EVIDENCE / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((EVIDENCE / manifest["parity_report"]).read_text(encoding="utf-8"))

    assert manifest["format"] == "NFS.GhidraExporterParityEvidence/1"
    assert manifest["program"]["name"] == "SHIFT.exe"
    assert manifest["program"]["sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert manifest["consumer_source_commit"] == "c125488b320af8fd864a519e4b7d856e7ebfd9c6"
    assert manifest["revenginstr_source_commit"] == "0645c5b41443e7e2ef085637017368449fd182be"
    assert manifest["query"] == {
        "kind": "exact_scalar_use",
        "scalar": "0x374",
        "record_count": 170,
    }
    assert manifest["fallback_retained"] is True

    assert report["format"] == "REVENGINSTR.GhidraJsonlExportParity/1"
    assert report["same_bytes"] is True
    assert report["same_records"] is True
    assert report["first_mismatch"] is None
    assert report["left_records"] == report["right_records"] == 170
    assert report["left_sha256"] == manifest["outputs"]["shared"]["sha256"]
    assert report["right_sha256"] == manifest["outputs"]["fallback"]["sha256"]


def test_function_instruction_shared_export_matches_legacy_fallback() -> None:
    evidence = ROOT / "evidence/ghidra_exporter_parity/function-instructions-00451280"
    manifest = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((evidence / manifest["parity_report"]).read_text(encoding="utf-8"))

    assert manifest["format"] == "NFS.GhidraExporterParityEvidence/1"
    assert manifest["program"]["sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert manifest["consumer_source_commit"] == "c125488b320af8fd864a519e4b7d856e7ebfd9c6"
    assert manifest["revenginstr_source_commit"] == "0645c5b41443e7e2ef085637017368449fd182be"
    assert manifest["query"] == {
        "kind": "function_instruction_export",
        "function_address": "0x00451280",
        "function_count": 1,
        "instruction_count": 2962,
    }
    assert manifest["fallback_retained"] is True

    assert report["format"] == "REVENGINSTR.GhidraJsonlExportParity/1"
    assert report["same_bytes"] is True
    assert report["same_records"] is True
    assert report["first_mismatch"] is None
    assert report["left_records"] == report["right_records"] == 1
    assert report["left_sha256"] == manifest["outputs"]["shared"]["sha256"]
    assert report["right_sha256"] == manifest["outputs"]["fallback"]["sha256"]

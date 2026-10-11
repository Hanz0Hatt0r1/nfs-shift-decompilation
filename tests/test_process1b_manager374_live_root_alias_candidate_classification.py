from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/shift_live_dump/classify_manager374_root_alias_candidates.py"


def module():
    spec = importlib.util.spec_from_file_location("manager374_alias_classification", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def binary_payload(**overrides):
    payload = {
        "format": "SHIFT.GhidraEvidenceDatabase/1",
        "program_name": "SHIFT.exe",
        "executable_md5": "705af8b420e5eb1e3834ac43d5533c6b",
        "language_id": "x86:LE:32:default",
        "image_base": "0x00400000",
        "pointer_size": 4,
        "memory_blocks": [
            {
                "name": ".text",
                "start": "0x00401000",
                "end": "0x00aa55ff",
                "initialized": True,
                "read": True,
                "write": False,
                "execute": True,
            },
            {
                "name": ".data",
                "start": "0x00b81000",
                "end": "0x00ce803f",
                "initialized": True,
                "read": True,
                "write": True,
                "execute": False,
            },
        ],
    }
    payload.update(overrides)
    return payload


def capture_payload(candidates: list[dict], *, roots=None):
    roots = roots or [
        {"snapshot": "snapshot-000000", "root_value": "0x11111000"},
        {"snapshot": "snapshot-000001", "root_value": "0x22222000"},
    ]
    return {
        "format": "SHIFT.P1B.Manager374RuntimeExactRootAliasCapture/1",
        "version": 1,
        "ready": True,
        "authority": {
            "canonical_root_slot": "0x00bc185c",
            "pointer_width_bits": 32,
            "little_endian": True,
        },
        "capture": {
            "active_nonzero_root_snapshot_count": len(roots),
            "active_root_values": roots,
        },
        "surface": {
            "exact_outer_root_alias_candidate_count": len(candidates),
            "exact_outer_root_alias_candidates": candidates,
        },
    }


def candidate(address: str, hits: list[str], roots: list[str], *, category="heap", path="[heap]", perms="rw-p"):
    return {
        "address": address,
        "region_start": address,
        "offset": 0,
        "perms": perms,
        "path": path,
        "category": category,
        "snapshot_hit_count": len(hits),
        "snapshot_hits": hits,
        "unique_root_value_count": len(roots),
        "root_values": roots,
    }


def prepare(tmp_path: Path, capture: dict, *, binary=None, globals_rows=None):
    capture_path = tmp_path / "capture.json"
    binary_path = tmp_path / "binary.json"
    globals_path = tmp_path / "globals.jsonl"
    write_json(capture_path, capture)
    write_json(binary_path, binary or binary_payload())
    write_jsonl(globals_path, globals_rows or [])
    return capture_path, binary_path, globals_path


def test_classifies_image_heap_and_anonymous_candidates(tmp_path: Path) -> None:
    mod = module()
    capture = capture_payload([
        candidate(
            "0x00b82000",
            ["snapshot-000000", "snapshot-000001"],
            ["0x11111000", "0x22222000"],
            category="module",
            path="/game/SHIFT.exe",
        ),
        candidate(
            "0x20000020",
            ["snapshot-000000"],
            ["0x11111000"],
            category="heap",
            path="[heap]",
        ),
        candidate(
            "0x30000010",
            ["snapshot-000000", "snapshot-000001"],
            ["0x11111000", "0x22222000"],
            category="anonymous",
            path="",
        ),
    ])
    paths = prepare(
        tmp_path,
        capture,
        globals_rows=[
            {"address": "0x00b82000", "name": "DAT_00b82000", "data_type": "undefined4", "xref_count": 3}
        ],
    )

    data = mod.analyze(*paths)
    assert data["format"] == "SHIFT.P1B.Manager374RuntimeRootAliasCandidateClassification/1"
    assert data["surface"]["classified_candidate_count"] == 3
    assert data["surface"]["storage_class_counts"] == {
        "anonymous": 1,
        "heap": 1,
        "retail-image-writable": 1,
    }
    assert data["surface"]["lifetime_class_counts"] == {
        "intermittent-over-supplied-capture": 1,
        "persistent-tracks-root-changes": 2,
    }
    assert data["surface"]["persistent_root_change_tracking_candidate_count"] == 2
    assert data["surface"]["retail_image_exact_global_candidate_count"] == 1

    image = next(row for row in data["surface"]["candidates"] if row["address"] == "0x00b82000")
    assert image["storage_class"] == "retail-image-writable"
    assert image["retail_memory_block"]["name"] == ".data"
    assert image["exact_ghidra_globals"][0]["name"] == "DAT_00b82000"
    assert image["covers_all_active_snapshots"] is True
    assert image["tracks_all_observed_root_values"] is True
    assert image["lifetime_class"] == "persistent-tracks-root-changes"

    adj = data["adjudication"]
    assert adj["supplied_capture_alias_candidates_classified"] is True
    assert adj["persistent_root_change_tracking_candidates_identified"] is True
    assert adj["retail_image_exact_global_candidates_identified"] is True
    assert adj["external_or_unknown_origin_outer_alias_surface_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_zero_candidates_still_do_not_promote_global_absence(tmp_path: Path) -> None:
    mod = module()
    paths = prepare(tmp_path, capture_payload([]))
    data = mod.analyze(*paths)
    assert data["surface"]["classified_candidate_count"] == 0
    assert data["adjudication"]["supplied_capture_alias_candidates_classified"] is True
    assert data["adjudication"]["persistent_root_change_tracking_candidates_identified"] is False
    assert data["adjudication"]["external_or_unknown_origin_outer_alias_surface_complete"] is False
    assert data["adjudication"]["global_manager_root_origin_surface_complete"] is False


def test_persistent_same_value_is_not_root_change_tracking(tmp_path: Path) -> None:
    mod = module()
    roots = [
        {"snapshot": "snapshot-000000", "root_value": "0x11111000"},
        {"snapshot": "snapshot-000001", "root_value": "0x11111000"},
    ]
    capture = capture_payload([
        candidate(
            "0x20000020",
            ["snapshot-000000", "snapshot-000001"],
            ["0x11111000"],
        )
    ], roots=roots)
    data = mod.analyze(*prepare(tmp_path, capture))
    row = data["surface"]["candidates"][0]
    assert row["covers_all_active_snapshots"] is True
    assert row["tracks_all_observed_root_values"] is True
    assert row["lifetime_class"] == "persistent-over-supplied-capture"
    assert data["surface"]["persistent_root_change_tracking_candidate_count"] == 0


def test_duplicate_candidate_and_count_drift_fail_closed(tmp_path: Path) -> None:
    mod = module()
    row = candidate("0x20000020", ["snapshot-000000"], ["0x11111000"])
    capture = capture_payload([row, dict(row)])
    with pytest.raises(ValueError, match="duplicate candidate address"):
        mod.analyze(*prepare(tmp_path, capture))

    bad = candidate("0x20000020", ["snapshot-000000"], ["0x11111000"])
    bad["snapshot_hit_count"] = 2
    with pytest.raises(ValueError, match="snapshot hit count drift"):
        mod.analyze(*prepare(tmp_path, capture_payload([bad])))


def test_binary_identity_drift_fails_closed(tmp_path: Path) -> None:
    mod = module()
    capture = capture_payload([])
    with pytest.raises(ValueError, match="unexpected executable MD5"):
        mod.analyze(*prepare(
            tmp_path,
            capture,
            binary=binary_payload(executable_md5="00000000000000000000000000000000"),
        ))

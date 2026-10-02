import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "build_lifecycle_investigation_targets.py"
    spec = importlib.util.spec_from_file_location("build_lifecycle_investigation_targets", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_builds_one_hop_slices_for_lifecycle_ready_classes(tmp_path):
    module = _load_module()
    scorecard = {
        "format": "SHIFT-CLASS-EVIDENCE-SCORECARD/1",
        "rows": [
            {
                "class_name": "AISegmentPath",
                "descriptor": 0x00C0D668,
                "parent_class": "AIPath",
                "field_count": 10,
                "unique_vtable": 0x00AFC930,
                "ghidra_registration_address": "0x00a84580",
                "unambiguous_initializer": "FUN_006cfe70",
                "evidence_tier": "lifecycle-investigation-ready",
            },
            {
                "class_name": "StructuralOnly",
                "descriptor": 0x1234,
                "field_count": 3,
                "evidence_tier": "structural-ready",
            },
        ],
    }
    scorecard_path = tmp_path / "scorecard.json"
    scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")

    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_jsonl(
        ghidra / "functions.jsonl",
        [
            {
                "address": "0x006cfe70",
                "name": "FUN_006cfe70",
                "size": 128,
                "calling_convention": "__thiscall",
                "signature": "undefined FUN_006cfe70(void)",
                "mnemonic_sha256": "init-fingerprint",
            },
            {
                "address": "0x00a84580",
                "name": "FUN_00a84580",
                "size": 86,
                "calling_convention": "__stdcall",
                "signature": "undefined FUN_00a84580(void)",
                "mnemonic_sha256": "reg-fingerprint",
            },
            {"address": "0x006d8490", "name": "FUN_006d8490", "size": 64},
            {"address": "0x006c1000", "name": "FUN_006c1000", "size": 32},
            {"address": "0x00631740", "name": "FUN_00631740", "size": 32},
        ],
    )
    _write_jsonl(
        ghidra / "callgraph.jsonl",
        [
            {
                "from_function": "0x006d8490",
                "from_name": "FUN_006d8490",
                "instruction": "0x006d84b6",
                "to": "0x006cfe70",
                "to_name": "FUN_006cfe70",
                "indirect": False,
            },
            {
                "from_function": "0x006cfe70",
                "from_name": "FUN_006cfe70",
                "instruction": "0x006cfe90",
                "to": "0x006c1000",
                "to_name": "FUN_006c1000",
                "indirect": False,
            },
            {
                "from_function": "0x00a84580",
                "from_name": "FUN_00a84580",
                "instruction": "0x00a8458c",
                "to": "0x00631740",
                "to_name": "FUN_00631740",
                "indirect": False,
            },
        ],
    )
    _write_jsonl(
        ghidra / "strings_xrefs.jsonl",
        [
            {
                "address": "0x00afc9d0",
                "value": "AISegmentPath",
                "functions": ["0x00a84580"],
            },
            {
                "address": "0x00afca00",
                "value": ".\\Source\\AI\\AISegmentPath.cpp",
                "functions": ["0x006cfe70"],
            },
        ],
    )

    report = module.build_targets(scorecard_path, ghidra)
    assert report["target_count"] == 1
    assert report["complete_slice_count"] == 1
    assert report["incomplete_slice_count"] == 0

    target = report["targets"][0]
    assert target["class_name"] == "AISegmentPath"
    assert target["slice_complete"] is True
    assert target["initializer"]["address"] == "0x006cfe70"
    assert target["initializer"]["mnemonic_sha256"] == "init-fingerprint"
    assert target["initializer"]["strings"] == [".\\Source\\AI\\AISegmentPath.cpp"]
    assert target["initializer"]["incoming_direct_calls"][0]["from_function"] == "0x006d8490"
    assert target["initializer"]["outgoing_direct_calls"][0]["to"] == "0x006c1000"
    assert target["registration"]["strings"] == ["AISegmentPath"]
    assert target["registration"]["outgoing_direct_calls"][0]["to"] == "0x00631740"
    assert report["scope"]["constructor_identity_inferred"] is False
    assert report["scope"]["destructor_identity_inferred"] is False


def test_missing_initializer_remains_incomplete(tmp_path):
    module = _load_module()
    scorecard = {
        "format": "SHIFT-CLASS-EVIDENCE-SCORECARD/1",
        "rows": [
            {
                "class_name": "MissingInit",
                "descriptor": 1,
                "field_count": 1,
                "ghidra_registration_address": "0x00100000",
                "unambiguous_initializer": "FUN_00200000",
                "evidence_tier": "lifecycle-investigation-ready",
            }
        ],
    }
    scorecard_path = tmp_path / "scorecard.json"
    scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_jsonl(
        ghidra / "functions.jsonl",
        [{"address": "0x00100000", "name": "FUN_00100000"}],
    )
    _write_jsonl(ghidra / "callgraph.jsonl", [])
    _write_jsonl(ghidra / "strings_xrefs.jsonl", [])

    report = module.build_targets(scorecard_path, ghidra)
    assert report["complete_slice_count"] == 0
    assert report["incomplete_slice_count"] == 1
    target = report["targets"][0]
    assert target["checks"]["initializer_present_in_ghidra"] is False
    assert target["slice_complete"] is False

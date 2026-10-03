import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "ghidra"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "build_static_semantic_index.py"
        spec = importlib.util.spec_from_file_location("build_static_semantic_index", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _source(md5="abc"):
    return {
        "program": "SHIFT.exe",
        "executable_md5": md5,
        "language_id": "x86:LE:32:default",
        "image_base": "0x00400000",
        "pointer_size": 4,
    }


def test_builds_static_semantic_index_and_preserves_layer_boundaries(tmp_path, monkeypatch):
    module = _load_module()

    crosscheck = {
        "format": "SHIFT.GhidraCrosscheckEvidence/1",
        "source": _source(),
        "anchors": [
            {
                "checks": {
                    "function_present": True,
                    "expected_strings": {"A": True},
                    "expected_calls": {"0x1": True},
                }
            },
            {
                "checks": {
                    "function_present": True,
                    "expected_strings": {"B": False},
                    "expected_calls": {},
                }
            },
        ],
        "rtti_registration_fingerprint": {
            "matching_function_count": 254,
            "registration_shape_match_count": 240,
        },
    }
    subsystem = {
        "format": "SHIFT.GhidraSubsystemManifestIndex/1",
        "source": _source(),
        "subsystems": {
            "renderer": {
                "semantic_aliases": [
                    {"address": "0x1", "promoted": True},
                    {"address": "0x2", "promoted": False},
                ],
                "class_registrations": [],
            },
            "ai": {
                "semantic_aliases": [],
                "class_registrations": [
                    {"address": "0x3", "promoted": True},
                    {"address": "0x4", "promoted": False},
                ],
            },
        },
        "semantic_aliases": [{"address": "0x1", "promoted": True}],
    }
    method_anchors = {
        "format": "SHIFT.GhidraMethodNameAnchors/1",
        "method_string_anchor_count": 90,
        "unique_method_name_candidate_count": 40,
        "ambiguous_method_anchor_function_count": 7,
    }
    joined = {
        "format": "SHIFT.GhidraSubsystemMethodAnchors/1",
        "source": _source(),
        "promoted_method_name_candidate_count": 12,
        "namespace_only_candidate_count": 9,
        "slice_only_unclassified_candidate_count": 3,
    }

    monkeypatch.setattr(module, "analyze_shift_export", lambda root: crosscheck)
    monkeypatch.setattr(module, "build_subsystem_manifests", lambda root: subsystem)
    monkeypatch.setattr(module, "discover_method_name_anchors", lambda root: method_anchors)
    monkeypatch.setattr(module, "join_method_anchors_to_subsystems", lambda root: joined)

    def fake_write_bundle(report, output_dir):
        assert report is subsystem
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "index.json").write_text(
            json.dumps({"format": report["format"]}) + "\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(module, "write_subsystem_bundle", fake_write_bundle)

    out = tmp_path / "semantic"
    report = module.build_static_semantic_index(tmp_path / "ghidra", out)

    assert report["format"] == "SHIFT.GhidraStaticSemanticIndex/1"
    assert report["source"]["executable_md5"] == "abc"
    assert report["counts"] == {
        "crosscheck_anchor_count": 2,
        "crosscheck_anchor_failure_count": 1,
        "registry_fingerprint_matches": 254,
        "registry_callshape_matches": 240,
        "semantic_alias_candidates": 2,
        "semantic_aliases_promoted": 1,
        "semantic_alias_mismatches": 1,
        "class_registration_candidates": 2,
        "class_registrations_promoted": 1,
        "class_registration_mismatches": 1,
        "method_string_anchors": 90,
        "unique_method_name_candidates": 40,
        "ambiguous_method_anchor_functions": 7,
        "subsystem_crosschecked_method_name_candidates": 12,
        "namespace_only_method_name_candidates": 9,
        "slice_only_unclassified_method_name_candidates": 3,
        "direct_evidence_mismatch_count": 3,
    }
    assert report["scope"]["heuristic_vtables_used"] is False
    assert report["scope"]["heuristic_constructors_used"] is False
    assert report["scope"]["heuristic_factories_used"] is False
    assert report["scope"]["automatic_function_renaming_performed"] is False

    expected = {
        "crosscheck.json",
        "method_name_anchors.json",
        "subsystem_method_anchors.json",
        "manifest.json",
        "subsystems",
    }
    assert {path.name for path in out.iterdir()} == expected
    assert (out / "subsystems" / "index.json").is_file()
    saved = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert saved["counts"] == report["counts"]


def test_rejects_mixed_executable_identity():
    module = _load_module()
    first = {"source": _source("aaa")}
    second = {"source": _source("bbb")}
    try:
        module._validate_source_identity(first, second)
    except ValueError as exc:
        assert "executable MD5" in str(exc)
    else:
        raise AssertionError("mixed Ghidra exports must be rejected")


def test_anchor_failure_count_checks_each_direct_requirement():
    module = _load_module()
    report = {
        "anchors": [
            {
                "checks": {
                    "function_present": False,
                    "expected_strings": {"A": False, "B": True},
                    "expected_calls": {"0x1": False, "0x2": True},
                }
            }
        ]
    }
    assert module._anchor_failure_count(report) == 3

import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "ghidra"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "build_proven_callgraph_frontier.py"
        spec = importlib.util.spec_from_file_location(
            "build_proven_callgraph_frontier", path
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _write_jsonl(path: Path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _function(address, name, *, external=False):
    return {
        "address": address,
        "name": name,
        "namespace": "Global",
        "size": 32,
        "thunk": False,
        "external": external,
        "calling_convention": "__cdecl",
        "signature": f"void {name}(void)",
        "parameters": [],
        "mnemonic_sha256": "a" * 64,
    }


def test_expands_anonymous_direct_frontier_and_preserves_ordering_evidence(
    tmp_path, monkeypatch
):
    module = _load_module()
    subsystem_report = {
        "format": "SHIFT.GhidraSubsystemManifestIndex/1",
        "source": {"program": "SHIFT.exe", "executable_md5": "abc"},
        "subsystems": {
            "physics": {
                "semantic_aliases": [
                    {"address": "0x00001000", "promoted": True},
                ],
                "class_registrations": [],
                "direct_call_edges": [],
            },
            "vehicle": {
                "semantic_aliases": [
                    {"address": "0x00002000", "promoted": True},
                ],
                "class_registrations": [],
                "direct_call_edges": [],
            },
        },
    }
    monkeypatch.setattr(
        module, "build_subsystem_manifests", lambda root: subsystem_report
    )

    _write_jsonl(
        tmp_path / "functions.jsonl",
        [
            _function("0x00001000", "FUN_00001000"),
            _function("0x00002000", "FUN_00002000"),
            _function("0x00003000", "FUN_00003000"),
            _function("0x00003100", "FUN_00003100"),
            _function("0x00003200", "FUN_00003200"),
            _function("0x00004000", "EXT_00004000", external=True),
        ],
    )
    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            {
                "from_function": "0x00003000",
                "from_name": "FUN_00003000",
                "instruction": "0x00003020",
                "to": "0x00002000",
                "to_name": "FUN_00002000",
                "indirect": False,
            },
            {
                "from_function": "0x00003000",
                "from_name": "FUN_00003000",
                "instruction": "0x00003010",
                "to": "0x00001000",
                "to_name": "FUN_00001000",
                "indirect": False,
            },
            {
                "from_function": "0x00001000",
                "from_name": "FUN_00001000",
                "instruction": "0x00001008",
                "to": "0x00003100",
                "to_name": "FUN_00003100",
                "indirect": False,
            },
            {
                "from_function": "0x00003200",
                "from_name": "FUN_00003200",
                "instruction": "0x00003208",
                "to": "0x00003000",
                "to_name": "FUN_00003000",
                "indirect": False,
            },
            {
                "from_function": "0x00002000",
                "from_name": "FUN_00002000",
                "instruction": "0x00002008",
                "to": "0x00004000",
                "to_name": "EXT_00004000",
                "indirect": False,
            },
            {
                "from_function": "0x00003000",
                "from_name": "FUN_00003000",
                "instruction": "0x00003030",
                "to": None,
                "to_name": None,
                "indirect": True,
            },
        ],
    )

    report = module.build_proven_callgraph_frontier(
        tmp_path,
        subsystems=("physics", "vehicle"),
        max_depth=2,
        max_targets=16,
    )

    assert report["format"] == "SHIFT.GhidraProvenCallgraphFrontier/1"
    assert report["proven_slice_address_count"] == 2
    assert report["frontier_candidate_count"] == 4
    assert report["direct_frontier_candidate_count"] == 3
    assert report["transitive_frontier_candidate_count"] == 1
    assert report["multi_anchor_caller_candidate_count"] == 1
    assert report["indirect_blocker_count"] == 1

    by_address = {
        row["address"]: row for row in report["frontier_candidates"]
    }
    bridge = by_address["0x00003000"]
    assert bridge["min_depth"] == 1
    assert bridge["subsystem_distances"] == {"physics": 1, "vehicle": 1}
    assert bridge["connected_subsystems"] == ["physics", "vehicle"]
    assert bridge["multi_anchor_caller_candidate"] is True
    assert bridge["promoted"] is False
    assert [
        edge["instruction"] for edge in bridge["ordered_slice_calls"]
    ] == ["0x00003010", "0x00003020"]
    assert bridge["adjacent_proven_slice_addresses"] == [
        "0x00001000",
        "0x00002000",
    ]
    assert bridge["indirect_call_sites"][0]["instruction"] == "0x00003030"

    caller = by_address["0x00003100"]
    assert caller["min_depth"] == 1
    assert caller["slice_callers"][0]["from_function"] == "0x00001000"

    transitive = by_address["0x00003200"]
    assert transitive["min_depth"] == 2
    assert transitive["status"] == "transitive-direct-callgraph-frontier"

    external = by_address["0x00004000"]
    assert external["external"] is True
    assert "0x00004000" not in report["instruction_export_addresses"]

    assert report["instruction_export_addresses"][0] == "0x00003000"
    assert report["scope"]["frontier_membership_is_semantic_promotion"] is False
    assert report["scope"]["multi_anchor_caller_is_update_loop_proof"] is False


def test_missing_export_files_fail_closed(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "build_subsystem_manifests",
        lambda root: {
            "subsystems": {
                "physics": {
                    "semantic_aliases": [
                        {"address": "0x00001000", "promoted": True}
                    ],
                    "class_registrations": [],
                    "direct_call_edges": [],
                },
                "vehicle": {
                    "semantic_aliases": [
                        {"address": "0x00002000", "promoted": True}
                    ],
                    "class_registrations": [],
                    "direct_call_edges": [],
                },
            }
        },
    )

    try:
        module.build_proven_callgraph_frontier(tmp_path)
    except FileNotFoundError as exc:
        assert "functions.jsonl" in str(exc)
    else:
        raise AssertionError("frontier must require the structured function export")


def test_unknown_subsystem_fails_closed(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "build_subsystem_manifests",
        lambda root: {"subsystems": {"physics": {}}},
    )
    try:
        module.build_proven_callgraph_frontier(
            tmp_path, subsystems=("body",), max_depth=1
        )
    except ValueError as exc:
        assert "unknown subsystem" in str(exc)
    else:
        raise AssertionError("unknown subsystem must not be silently invented")

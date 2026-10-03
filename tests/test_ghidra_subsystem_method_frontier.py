import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "ghidra"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "build_subsystem_method_frontier.py"
        spec = importlib.util.spec_from_file_location(
            "build_subsystem_method_frontier", path
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


def test_builds_one_hop_frontier_without_promoting_candidates(tmp_path, monkeypatch):
    module = _load_module()

    subsystem_report = {
        "format": "SHIFT.GhidraSubsystemManifestIndex/1",
        "source": {"program": "SHIFT.exe", "executable_md5": "abc"},
        "subsystems": {
            "physics": {
                "semantic_aliases": [
                    {"address": "0x00750080", "promoted": True},
                ],
                "class_registrations": [],
                "direct_call_edges": [
                    {
                        "from_function": "0x00750080",
                        "instruction": "0x00750573",
                        "to": "0x00710860",
                        "indirect": False,
                    }
                ],
            },
            "vehicle": {
                "semantic_aliases": [
                    {"address": "0x00798df0", "promoted": True},
                ],
                "class_registrations": [],
                "direct_call_edges": [],
            },
            "renderer": {
                "semantic_aliases": [],
                "class_registrations": [],
                "direct_call_edges": [],
            },
            "scene_graph": {
                "semantic_aliases": [],
                "class_registrations": [],
                "direct_call_edges": [],
            },
            "ai": {
                "semantic_aliases": [],
                "class_registrations": [],
                "direct_call_edges": [],
            },
        },
    }
    joined = {
        "format": "SHIFT.GhidraSubsystemMethodAnchors/1",
        "unique_candidates": [
            {
                "address": "0x0079cd90",
                "ghidra_name": "FUN_0079cd90",
                "method_name": "MWL::Core::PhysicsAllocator::malloc",
                "namespace_subsystem": "physics",
                "promoted": False,
                "calling_convention": "__thiscall",
                "size": 116,
                "mnemonic_sha256": "a" * 64,
                "anchor_string_addresses": ["0x00b0b8fc"],
            },
            {
                "address": "0x00710870",
                "ghidra_name": "FUN_00710870",
                "method_name": "MWL::Core::cPhysicsManager::GetAssetDatabase",
                "namespace_subsystem": "physics",
                "promoted": False,
                "calling_convention": "__stdcall",
                "size": 65,
                "mnemonic_sha256": "b" * 64,
                "anchor_string_addresses": ["0x00b044c0"],
            },
            {
                "address": "0x00799990",
                "ghidra_name": "FUN_00799990",
                "method_name": "MWL::Core::VehicleFactory::Create",
                "namespace_subsystem": "vehicle",
                "promoted": False,
                "calling_convention": "__cdecl",
                "size": 32,
                "mnemonic_sha256": "c" * 64,
                "anchor_string_addresses": ["0x00b10000"],
            },
            {
                "address": "0x00750080",
                "ghidra_name": "FUN_00750080",
                "method_name": "MWL::Core::LoadCollisionStream",
                "namespace_subsystem": "physics",
                "promoted": True,
            },
        ],
        "ambiguous_functions": [
            {
                "address": "0x0079db50",
                "ghidra_name": "FUN_0079db50",
                "method_anchors": [
                    "MWL::PhysicsEvent_Impact::SetObjectID",
                    "MWL::PhysicsEvent_Impact::SetObjectMass",
                ],
                "namespace_subsystems": ["physics"],
                "promoted": False,
            }
        ],
    }

    monkeypatch.setattr(module, "build_subsystem_manifests", lambda root: subsystem_report)
    monkeypatch.setattr(module, "join_method_anchors_to_subsystems", lambda root: joined)

    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            {
                "from_function": "0x0079cd90",
                "from_name": "FUN_0079cd90",
                "instruction": "0x0079cdb5",
                "to": "0x00710860",
                "to_name": "FUN_00710860",
                "indirect": False,
            },
            {
                "from_function": "0x00710870",
                "from_name": "FUN_00710870",
                "instruction": "0x00710871",
                "to": "0x0070fe90",
                "to_name": "FUN_0070fe90",
                "indirect": False,
            },
            {
                "from_function": "0x00798df0",
                "from_name": "FUN_00798df0",
                "instruction": "0x00798e10",
                "to": "0x00799990",
                "to_name": "FUN_00799990",
                "indirect": False,
            },
            {
                "from_function": "0x0079db50",
                "from_name": "FUN_0079db50",
                "instruction": "0x0079dba0",
                "to": "0x00710860",
                "to_name": "FUN_00710860",
                "indirect": False,
            },
            {
                "from_function": "0x00710870",
                "from_name": "FUN_00710870",
                "instruction": "0x00710875",
                "to": "0x00710860",
                "to_name": "FUN_00710860",
                "indirect": True,
            },
        ],
    )

    report = module.build_subsystem_method_frontier(tmp_path)
    assert report["format"] == "SHIFT.GhidraSubsystemMethodFrontier/1"
    assert report["namespace_only_candidate_count"] == 3
    assert report["one_hop_frontier_candidate_count"] == 2
    assert report["namespace_only_no_one_hop_link_count"] == 1
    assert report["ambiguous_near_slice_count"] == 1

    by_address = {
        row["address"]: row
        for row in report["frontier_candidates"]
    }
    malloc = by_address["0x0079cd90"]
    assert malloc["subsystem"] == "physics"
    assert malloc["direct_link_directions"] == ["candidate-to-slice"]
    assert malloc["connected_slice_addresses"] == ["0x00710860"]
    assert malloc["frontier_candidate"] is True
    assert malloc["promoted"] is False

    vehicle = by_address["0x00799990"]
    assert vehicle["subsystem"] == "vehicle"
    assert vehicle["direct_link_directions"] == ["slice-to-candidate"]
    assert vehicle["connected_slice_addresses"] == ["0x00798df0"]
    assert vehicle["promoted"] is False

    disconnected = report["namespace_only_without_one_hop_link"]
    assert [row["address"] for row in disconnected] == ["0x00710870"]
    assert disconnected[0]["status"] == "namespace-only-no-one-hop-link"

    ambiguous = report["ambiguous_near_slice"][0]
    assert ambiguous["address"] == "0x0079db50"
    assert ambiguous["frontier_candidate"] is False
    assert ambiguous["promoted"] is False

    assert report["scope"]["one_hop_link_is_semantic_promotion"] is False
    assert report["scope"]["ambiguous_functions_promoted"] is False


def test_missing_callgraph_fails_closed(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "build_subsystem_manifests",
        lambda root: {"subsystems": {}, "source": {}},
    )
    monkeypatch.setattr(
        module,
        "join_method_anchors_to_subsystems",
        lambda root: {"unique_candidates": [], "ambiguous_functions": []},
    )
    try:
        module.build_subsystem_method_frontier(tmp_path)
    except FileNotFoundError as exc:
        assert "callgraph.jsonl" in str(exc)
    else:
        raise AssertionError("frontier analysis must require direct callgraph evidence")

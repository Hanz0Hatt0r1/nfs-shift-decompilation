import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "ghidra"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "build_construction_frontier.py"
        spec = importlib.util.spec_from_file_location("build_construction_frontier", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _function(address, name, *, external=False, thunk=False):
    return {
        "address": address,
        "name": name,
        "namespace": "Global",
        "size": 64,
        "thunk": thunk,
        "external": external,
        "calling_convention": "__thiscall",
        "signature": f"void {name}(void)",
        "parameters": [],
        "mnemonic_sha256": "a" * 64,
    }


def _call(source, instruction, target):
    return {
        "from_function": source,
        "from_name": f"FUN_{source[-4:]}",
        "instruction": instruction,
        "to": target,
        "to_name": f"FUN_{target[-4:]}",
        "indirect": False,
    }


def _subsystem_report():
    return {
        "source": {"program": "SHIFT.exe", "executable_md5": "abc"},
        "subsystems": {
            "physics": {
                "semantic_aliases": [{"address": "0x00001000", "promoted": True}],
                "class_registrations": [],
                "direct_call_edges": [],
            },
            "vehicle": {
                "semantic_aliases": [{"address": "0x00002000", "promoted": True}],
                "class_registrations": [],
                "direct_call_edges": [],
            },
        },
    }


def test_joins_vtable_xrefs_to_proven_slices_without_constructor_promotion(
    tmp_path, monkeypatch
):
    module = _load_module()
    monkeypatch.setattr(module, "build_subsystem_manifests", lambda root: _subsystem_report())

    _write_jsonl(
        tmp_path / "functions.jsonl",
        [
            _function("0x00001000", "PhysicsAnchor"),
            _function("0x00002000", "VehicleAnchor"),
            _function("0x00003000", "FUN_00003000"),
            _function("0x00003100", "FUN_00003100"),
            _function("0x00003200", "FUN_00003200"),
        ],
    )
    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            _call("0x00003000", "0x00003010", "0x00001000"),
            _call("0x00003100", "0x00003110", "0x00003000"),
        ],
    )
    (tmp_path / "vtables.json").write_text(
        json.dumps(
            {
                "format": "SHIFT.GhidraVtableCandidates/1",
                "status": "heuristic-candidates",
                "vtables": [
                    {
                        "address": "0x00005000",
                        "block": ".rdata",
                        "slot_count": 3,
                        "slots": [
                            {"slot": 0, "target": "0x00001000", "name": "PhysicsAnchor"},
                            {"slot": 1, "target": "0x00006000", "name": "FUN_00006000"},
                            {"slot": 2, "target": "0x00006100", "name": "FUN_00006100"},
                        ],
                        "function_xrefs": ["0x00003000", "0x00003200"],
                    },
                    {
                        "address": "0x00005100",
                        "block": ".rdata",
                        "slot_count": 3,
                        "slots": [
                            {"slot": 0, "target": "0x00007000", "name": "FUN_00007000"},
                            {"slot": 1, "target": "0x00007100", "name": "FUN_00007100"},
                            {"slot": 2, "target": "0x00007200", "name": "FUN_00007200"},
                        ],
                        "function_xrefs": ["0x00003100"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "constructors.jsonl",
        [
            {
                "status": "vtable-xref-candidate",
                "function": "0x00003000",
                "name": "FUN_00003000",
                "vtables": ["0x00005000"],
                "instruction_preview": ["0x00003000 PUSH EBP"],
            },
            {
                "status": "vtable-xref-candidate",
                "function": "0x00003100",
                "name": "FUN_00003100",
                "vtables": ["0x00005100"],
                "instruction_preview": [],
            },
            {
                "status": "vtable-xref-candidate",
                "function": "0x00003200",
                "name": "FUN_00003200",
                "vtables": ["0x00005000"],
                "instruction_preview": [],
            },
        ],
    )

    report = module.build_construction_frontier(tmp_path, max_depth=2, max_targets=8)

    assert report["format"] == "SHIFT.GhidraConstructionFrontier/1"
    assert report["heuristic_vtable_candidate_count"] == 2
    assert report["heuristic_constructor_candidate_count"] == 3
    assert report["frontier_candidate_count"] == 3
    assert report["unlinked_candidate_count"] == 0
    assert report["slot_linked_candidate_count"] == 2

    by_function = {row["function"]: row for row in report["frontier_candidates"]}
    direct = by_function["0x00003000"]
    assert direct["min_callgraph_depth"] == 1
    assert direct["status"] == "vtable-xref-direct-proven-slice-frontier"
    assert direct["has_proven_slice_slot_target"] is True
    assert direct["proven_slice_slot_targets"] == [
        {
            "vtable": "0x00005000",
            "slot": 0,
            "target": "0x00001000",
            "name": "PhysicsAnchor",
            "proven_subsystems": ["physics"],
            "status": "heuristic-vtable-slot-targets-proven-slice-function",
            "promoted": False,
        }
    ]
    assert direct["direct_proven_slice_edges"][0]["instruction"] == "0x00003010"
    assert direct["promoted"] is False

    transitive = by_function["0x00003100"]
    assert transitive["min_callgraph_depth"] == 2
    assert transitive["has_proven_slice_slot_target"] is False
    assert transitive["status"] == "vtable-xref-transitive-proven-slice-frontier"

    slot_only = by_function["0x00003200"]
    assert slot_only["min_callgraph_depth"] is None
    assert slot_only["status"] == "vtable-xref-with-proven-slice-slot-target"

    assert report["instruction_export_addresses"][0] == "0x00003000"
    assert report["scope"]["vtable_candidates_are_heuristic"] is True
    assert report["scope"]["constructor_identity_proven"] is False
    assert report["scope"]["vptr_store_proven"] is False
    assert report["scope"]["virtual_dispatch_target_proven"] is False


def test_unlinked_candidate_is_audited_but_not_exported(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "build_subsystem_manifests", lambda root: _subsystem_report())
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [
            _function("0x00001000", "PhysicsAnchor"),
            _function("0x00002000", "VehicleAnchor"),
            _function("0x00003000", "FUN_00003000"),
        ],
    )
    _write_jsonl(tmp_path / "callgraph.jsonl", [])
    (tmp_path / "vtables.json").write_text(
        json.dumps(
            {
                "format": "SHIFT.GhidraVtableCandidates/1",
                "status": "heuristic-candidates",
                "vtables": [
                    {
                        "address": "0x00005000",
                        "block": ".rdata",
                        "slot_count": 3,
                        "slots": [
                            {"slot": 0, "target": "0x00006000", "name": None},
                            {"slot": 1, "target": "0x00006100", "name": None},
                            {"slot": 2, "target": "0x00006200", "name": None},
                        ],
                        "function_xrefs": ["0x00003000"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "constructors.jsonl",
        [
            {
                "status": "vtable-xref-candidate",
                "function": "0x00003000",
                "name": "FUN_00003000",
                "vtables": ["0x00005000"],
                "instruction_preview": [],
            }
        ],
    )
    report = module.build_construction_frontier(tmp_path)
    assert report["frontier_candidate_count"] == 0
    assert report["unlinked_candidate_count"] == 1
    assert report["instruction_export_addresses"] == []
    assert report["unlinked_candidates"][0]["status"] == "vtable-xref-outside-selected-frontier"


def test_cross_file_vtable_xref_mismatch_fails_closed(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "build_subsystem_manifests", lambda root: _subsystem_report())
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [
            _function("0x00001000", "PhysicsAnchor"),
            _function("0x00002000", "VehicleAnchor"),
            _function("0x00003000", "FUN_00003000"),
        ],
    )
    _write_jsonl(tmp_path / "callgraph.jsonl", [])
    (tmp_path / "vtables.json").write_text(
        json.dumps(
            {
                "format": "SHIFT.GhidraVtableCandidates/1",
                "status": "heuristic-candidates",
                "vtables": [
                    {
                        "address": "0x00005000",
                        "block": ".rdata",
                        "slot_count": 3,
                        "slots": [{"slot": i, "target": f"0x00006{i}00", "name": None} for i in range(3)],
                        "function_xrefs": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "constructors.jsonl",
        [
            {
                "status": "vtable-xref-candidate",
                "function": "0x00003000",
                "name": "FUN_00003000",
                "vtables": ["0x00005000"],
                "instruction_preview": [],
            }
        ],
    )
    with pytest.raises(ValueError, match="cross-file vtable xref mismatch"):
        module.build_construction_frontier(tmp_path)


def test_missing_vtable_export_fails_closed(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "build_subsystem_manifests", lambda root: _subsystem_report())
    _write_jsonl(tmp_path / "functions.jsonl", [])
    _write_jsonl(tmp_path / "callgraph.jsonl", [])
    with pytest.raises(FileNotFoundError, match="vtables.json"):
        module.build_construction_frontier(tmp_path)

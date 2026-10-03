import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_indirect_dispatch_frontier.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_indirect_dispatch_frontier", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def _function(address):
    return {
        "address": address,
        "name": f"FUN_{address[2:]}",
        "size": 64,
        "external": False,
        "thunk": False,
        "calling_convention": "__thiscall",
        "signature": f"undefined FUN_{address[2:]}(void)",
        "mnemonic_sha256": address[2:].rjust(64, "0")[-64:],
    }


def _call(source, instruction, target=None, *, indirect=False):
    return {
        "from_function": source,
        "from_name": f"FUN_{source[2:]}",
        "instruction": instruction,
        "to": target,
        "to_name": f"FUN_{target[2:]}" if target else None,
        "indirect": indirect,
    }


def _fixture(tmp_path, *, with_vtable=True, with_raw=True):
    module = _load_module()
    target = "0x0079b2d0"
    owner = "0x00600000"
    helper = "0x00610000"
    vtable = "0x00aa0000"

    (tmp_path / "binary.json").write_text(
        json.dumps(
            {
                "program_name": "SHIFT.exe",
                "executable_md5": "705af8b420e5eb1e3834ac43d5533c6b",
                "language_id": "x86:LE:32:default",
                "image_base": "0x00400000",
                "pointer_size": 4,
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [_function(address) for address in (target, owner, helper)],
    )
    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            _call(target, "0x0079b330", helper),
            _call(target, "0x0079b350", None, indirect=True),
        ],
    )

    tables = []
    constructors = []
    if with_vtable:
        tables.append(
            {
                "address": vtable,
                "block": ".rdata",
                "slot_count": 3,
                "slots": [
                    {"slot": 0, "target": helper, "name": "FUN_00610000"},
                    {"slot": 1, "target": target, "name": "FUN_0079b2d0"},
                    {"slot": 2, "target": helper, "name": "FUN_00610000"},
                ],
                "function_xrefs": [owner],
            }
        )
        constructors.append(
            {
                "status": "vtable-xref-candidate",
                "function": owner,
                "name": "FUN_00600000",
                "vtables": [vtable],
                "instruction_preview": ["0x00600010 MOV dword ptr [ECX],0xaa0000"],
            }
        )
    (tmp_path / "vtables.json").write_text(
        json.dumps(
            {
                "format": module.VTABLE_FORMAT,
                "status": "heuristic-candidates",
                "vtables": tables,
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(tmp_path / "constructors.jsonl", constructors)

    raw = "00000000"
    if with_raw:
        raw += "d0b27900"
    raw += "00000000"
    _write_jsonl(
        tmp_path / "static_tables.jsonl",
        [
            {
                "address": "0x00bb0000",
                "block": ".data",
                "data_type": "undefined4[3]",
                "length": len(raw) // 2,
                "components": 3,
                "raw_hex": raw,
                "raw_truncated": False,
            }
        ],
    )
    _write_jsonl(
        tmp_path / "switches.jsonl",
        [
            {
                "status": "computed-jump-candidate",
                "function": target,
                "name": "FUN_0079b2d0",
                "instruction": "0x0079b2ec",
                "text": "JMP dword ptr [EAX*0x4 + 0x79b46c]",
                "destinations": ["0x0079b2f3", "0x0079b3a7"],
            }
        ],
    )
    _write_jsonl(
        tmp_path / "strings_xrefs.jsonl",
        [
            {
                "address": "0x00cc0000",
                "value": "owner hint",
                "functions": [owner],
            }
        ],
    )
    return module, target, owner, vtable


def test_builds_vtable_and_static_pointer_frontier(tmp_path):
    module, target, owner, vtable = _fixture(tmp_path)
    report = module.build_indirect_dispatch_frontier(tmp_path, [target])

    assert report["format"] == "SHIFT.GhidraIndirectDispatchFrontier/1"
    assert report["target_count"] == 1
    row = report["targets"][0]
    assert row["address"] == target
    assert row["direct_incoming_count"] == 0
    assert row["direct_incoming_absent_verified"] is True
    assert row["evidence_state"] == "ambiguous"
    assert row["dispatch_owner_proven"] is False

    assert len(row["vtable_memberships"]) == 1
    membership = row["vtable_memberships"][0]
    assert membership["vtable_address"] == vtable
    assert membership["matching_slots"] == [
        {"slot": 1, "target": target, "name": "FUN_0079b2d0"}
    ]
    assert membership["function_xrefs"] == [owner]
    assert membership["class_identity_proven"] is False

    assert len(row["constructor_candidates"]) == 1
    assert row["constructor_candidates"][0]["function"] == owner
    assert row["constructor_candidates"][0]["constructor_role_proven"] is False

    assert len(row["raw_static_pointer_occurrences"]) == 1
    occurrence = row["raw_static_pointer_occurrences"][0]
    assert occurrence["byte_offset"] == 4
    assert occurrence["cell_address"] == "0x00bb0004"
    assert occurrence["pointer_aligned"] is True
    assert occurrence["semantic_role_proven"] is False

    assert row["candidate_owner_functions"] == [owner]
    assert report["instruction_export_addresses"] == [owner, target]
    assert report["scope"]["vtable_candidates_are_heuristic"] is True
    assert report["scope"]["raw_pointer_occurrence_is_dispatch_proof"] is False


def test_raw_pointer_only_stays_ambiguous(tmp_path):
    module, target, *_ = _fixture(tmp_path, with_vtable=False, with_raw=True)
    report = module.build_indirect_dispatch_frontier(tmp_path, [target])
    row = report["targets"][0]
    assert row["evidence_state"] == "ambiguous"
    assert row["vtable_memberships"] == []
    assert len(row["raw_static_pointer_occurrences"]) == 1
    assert row["candidate_owner_functions"] == []


def test_no_pointer_evidence_stays_unknown(tmp_path):
    module, target, *_ = _fixture(tmp_path, with_vtable=False, with_raw=False)
    report = module.build_indirect_dispatch_frontier(tmp_path, [target])
    row = report["targets"][0]
    assert row["evidence_state"] == "unknown"
    assert row["dispatch_owner_proven"] is False
    assert report["instruction_export_addresses"] == [target]


def test_fails_closed_on_vtable_format_drift(tmp_path):
    module, target, *_ = _fixture(tmp_path)
    payload = json.loads((tmp_path / "vtables.json").read_text(encoding="utf-8"))
    payload["format"] = "SHIFT.GhidraVtableCandidates/999"
    (tmp_path / "vtables.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=module.VTABLE_FORMAT):
        module.build_indirect_dispatch_frontier(tmp_path, [target])


def test_fails_closed_when_target_is_not_a_function(tmp_path):
    module, *_ = _fixture(tmp_path)
    with pytest.raises(ValueError, match="absent from functions"):
        module.build_indirect_dispatch_frontier(tmp_path, ["0x00123456"])


def test_deduplicates_and_normalizes_targets(tmp_path):
    module, target, *_ = _fixture(tmp_path)
    report = module.build_indirect_dispatch_frontier(
        tmp_path, ["0X0079B2D0", target]
    )
    assert report["target_count"] == 1
    assert report["targets"][0]["address"] == target

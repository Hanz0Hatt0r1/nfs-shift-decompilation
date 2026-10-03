import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_vehicle_ownership_lifecycle_frontier.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_vehicle_ownership_lifecycle_frontier", path
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
        "size": 128,
        "external": False,
        "thunk": False,
        "calling_convention": "__thiscall",
        "signature": f"undefined FUN_{address[2:]}(void)",
        "mnemonic_sha256": address[2:] * 4,
    }


def _call(source, instruction, target):
    return {
        "from_function": source,
        "from_name": f"FUN_{source[2:]}",
        "instruction": instruction,
        "to": target,
        "to_name": f"FUN_{target[2:]}",
        "indirect": False,
    }


def _fixture(tmp_path):
    module = _load_module()
    caller_a = "0x00715700"
    caller_b = "0x00715800"
    parent_a = "0x00715000"
    lifecycle_a = "0x00715900"
    lifecycle_b = "0x0079a000"

    upper_contract = {
        "format": module.UPPER_CONTRACT_FORMAT,
        "anchors": {
            "outer_update": module.OUTER_UPDATE,
            "upper_caller": module.UPPER_CALLER,
            "alternate_caller": module.ALTERNATE_CALLER,
        },
        "closure": {
            "upper_direct_path": "verified",
            "path": [
                module.UPPER_CALLER,
                "0x00715380",
                "0x00713050",
                "0x00794a30",
                module.OUTER_UPDATE,
            ],
        },
    }
    upper_path = tmp_path / "upper.json"
    upper_path.write_text(json.dumps(upper_contract), encoding="utf-8")

    indirect = {
        "format": module.INDIRECT_FRONTIER_FORMAT,
        "targets": [
            {
                "address": module.ALTERNATE_CALLER,
                "direct_incoming_count": 0,
                "direct_incoming_absent_verified": True,
                "candidate_owner_functions": [lifecycle_b],
                "evidence_state": "ambiguous",
            }
        ],
    }
    indirect_path = tmp_path / "indirect.json"
    indirect_path.write_text(json.dumps(indirect), encoding="utf-8")

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

    addresses = {
        module.UPPER_CALLER,
        module.ALTERNATE_CALLER,
        module.OUTER_UPDATE,
        caller_a,
        caller_b,
        parent_a,
        lifecycle_a,
        lifecycle_b,
    }
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [_function(address) for address in sorted(addresses)],
    )

    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            _call(parent_a, "0x00715044", caller_a),
            _call(caller_a, "0x00715744", module.UPPER_CALLER),
            _call(caller_b, "0x00715855", module.UPPER_CALLER),
            _call(module.UPPER_CALLER, "0x00715602", "0x00715380"),
            _call(module.ALTERNATE_CALLER, "0x0079b310", module.OUTER_UPDATE),
        ],
    )

    (tmp_path / "vtables.json").write_text(
        json.dumps(
            {
                "format": module.VTABLE_FORMAT,
                "status": "heuristic-candidates",
                "vtables": [
                    {
                        "address": "0x00b10000",
                        "block": ".rdata",
                        "slot_count": 4,
                        "slots": [
                            {"slot": 2, "target": module.UPPER_CALLER, "name": "upper"}
                        ],
                        "function_xrefs": [caller_a, lifecycle_a],
                    },
                    {
                        "address": "0x00b20000",
                        "block": ".rdata",
                        "slot_count": 5,
                        "slots": [
                            {
                                "slot": 3,
                                "target": module.ALTERNATE_CALLER,
                                "name": "alternate",
                            }
                        ],
                        "function_xrefs": [lifecycle_b],
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
                "function": lifecycle_a,
                "name": f"FUN_{lifecycle_a[2:]}",
                "vtables": ["0x00b10000"],
                "instruction_preview": ["MOV dword ptr [ECX],0x00b10000"],
            },
            {
                "status": "vtable-xref-candidate",
                "function": lifecycle_b,
                "name": f"FUN_{lifecycle_b[2:]}",
                "vtables": ["0x00b20000"],
                "instruction_preview": ["MOV dword ptr [ECX],0x00b20000"],
            },
        ],
    )

    _write_jsonl(
        tmp_path / "strings_xrefs.jsonl",
        [
            {
                "value": "vehicle-update-debug-anchor",
                "functions": [caller_a],
            },
            {
                "value": "lifecycle-candidate-string",
                "functions": [lifecycle_a],
            },
        ],
    )

    return {
        "module": module,
        "upper": upper_path,
        "indirect": indirect_path,
        "caller_a": caller_a,
        "caller_b": caller_b,
        "parent_a": parent_a,
        "lifecycle_a": lifecycle_a,
        "lifecycle_b": lifecycle_b,
    }


def test_builds_exact_upper_caller_and_heuristic_lifecycle_frontier(tmp_path):
    fx = _fixture(tmp_path)
    module = fx["module"]
    report = module.build_vehicle_ownership_lifecycle_frontier(
        tmp_path, fx["upper"], fx["indirect"]
    )

    assert report["format"] == "SHIFT.VehicleOwnershipLifecycleFrontier/1"
    assert report["upper_direct_caller_count"] == 2
    assert report["alternate_direct_incoming_absent_verified"] is True
    assert [row["address"] for row in report["upper_direct_callers"]] == [
        fx["caller_a"],
        fx["caller_b"],
    ]

    callers = {row["address"]: row for row in report["upper_direct_callers"]}
    assert callers[fx["caller_a"]]["direct_calls_to_upper"][0]["instruction"] == "0x00715744"
    assert callers[fx["caller_b"]]["direct_calls_to_upper"][0]["instruction"] == "0x00715855"
    assert callers[fx["caller_a"]]["direct_incoming_count"] == 1
    assert callers[fx["caller_a"]]["owner_role_state"] == "unknown"
    assert callers[fx["caller_a"]]["lifecycle_role_state"] == "ambiguous"
    assert "function-xref-to-relevant-heuristic-vtable" in callers[fx["caller_a"]][
        "heuristic_lifecycle_overlap"
    ]
    assert callers[fx["caller_a"]]["strings"] == ["vehicle-update-debug-anchor"]

    assert report["upper_vtable_memberships"][0]["matching_slots"][0]["slot"] == 2
    assert report["alternate_vtable_memberships"][0]["matching_slots"][0]["slot"] == 3
    assert len(report["lifecycle_candidates"]) == 2
    assert all(
        row["constructor_role_proven"] is False
        for row in report["lifecycle_candidates"]
    )

    targets = set(report["instruction_export_addresses"])
    assert {
        module.UPPER_CALLER,
        module.ALTERNATE_CALLER,
        fx["caller_a"],
        fx["caller_b"],
        fx["lifecycle_a"],
        fx["lifecycle_b"],
    } <= targets
    assert report["scope"]["direct_caller_is_owner_proof"] is False
    assert report["scope"]["constructor_candidate_is_owner_proof"] is False


def test_fails_closed_when_upper_has_no_direct_callers(tmp_path):
    fx = _fixture(tmp_path)
    rows = [
        _call(fx["module"].ALTERNATE_CALLER, "0x0079b310", fx["module"].OUTER_UPDATE)
    ]
    _write_jsonl(tmp_path / "callgraph.jsonl", rows)

    with pytest.raises(ValueError, match="no direct caller of FUN_007155e9"):
        fx["module"].build_vehicle_ownership_lifecycle_frontier(
            tmp_path, fx["upper"], fx["indirect"]
        )


def test_fails_closed_when_alternate_gains_direct_caller(tmp_path):
    fx = _fixture(tmp_path)
    new_owner = "0x0079a100"
    with (tmp_path / "functions.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_function(new_owner)) + "\n")
    with (tmp_path / "callgraph.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(_call(new_owner, "0x0079a155", fx["module"].ALTERNATE_CALLER))
            + "\n"
        )

    with pytest.raises(ValueError, match="Ghidra callgraph disagrees"):
        fx["module"].build_vehicle_ownership_lifecycle_frontier(
            tmp_path, fx["upper"], fx["indirect"]
        )


def test_fails_closed_when_indirect_report_claims_direct_owner(tmp_path):
    fx = _fixture(tmp_path)
    payload = json.loads(fx["indirect"].read_text(encoding="utf-8"))
    payload["targets"][0]["direct_incoming_count"] = 1
    payload["targets"][0]["direct_incoming_absent_verified"] = False
    fx["indirect"].write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="acquired a direct incoming edge"):
        fx["module"].build_vehicle_ownership_lifecycle_frontier(
            tmp_path, fx["upper"], fx["indirect"]
        )


def test_fails_closed_on_upper_contract_path_drift(tmp_path):
    fx = _fixture(tmp_path)
    payload = json.loads(fx["upper"].read_text(encoding="utf-8"))
    payload["closure"]["path"][0] = "0x00715500"
    fx["upper"].write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="path endpoints changed"):
        fx["module"].build_vehicle_ownership_lifecycle_frontier(
            tmp_path, fx["upper"], fx["indirect"]
        )


def test_fails_closed_on_vtable_status_drift(tmp_path):
    fx = _fixture(tmp_path)
    payload = json.loads((tmp_path / "vtables.json").read_text(encoding="utf-8"))
    payload["status"] = "promoted-vtables"
    (tmp_path / "vtables.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="heuristic-candidates status"):
        fx["module"].build_vehicle_ownership_lifecycle_frontier(
            tmp_path, fx["upper"], fx["indirect"]
        )

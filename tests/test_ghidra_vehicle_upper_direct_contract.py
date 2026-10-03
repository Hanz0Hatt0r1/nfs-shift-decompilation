import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_vehicle_upper_direct_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_vehicle_upper_direct_contract", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _edge(source, instruction, target):
    return {
        "from_function": source,
        "from_name": f"FUN_{source[2:]}",
        "instruction": instruction,
        "to": target,
        "to_name": f"FUN_{target[2:]}",
        "indirect": False,
    }


def _direct(address, calls, incoming_count):
    return {
        "address": address,
        "name": f"FUN_{address[2:]}",
        "size": 128,
        "external": False,
        "thunk": False,
        "calling_convention": "__thiscall",
        "signature": f"undefined FUN_{address[2:]}(void)",
        "ordered_direct_calls": calls,
        "direct_incoming_count": incoming_count,
    }


def _upstream(address, depth, calls, incoming_count=1):
    return {
        "address": address,
        "name": f"FUN_{address[2:]}",
        "function_metadata_present": True,
        "external": False,
        "thunk": False,
        "calling_convention": "__thiscall",
        "signature": f"undefined FUN_{address[2:]}(void)",
        "size": 128,
        "upstream_depth": depth,
        "direct_incoming_count": incoming_count,
        "direct_outgoing_count": len(calls),
        "ordered_direct_calls": calls,
        "indirect_call_sites": [],
        "computed_jump_candidates": [],
        "promoted": False,
    }


def _fixture(tmp_path):
    module = _load_module()
    primary = _direct(
        module.PRIMARY_CALLER,
        [_edge(module.PRIMARY_CALLER, "0x00794a6e", module.OUTER_UPDATE)],
        3,
    )
    alternate = _direct(
        module.ALTERNATE_CALLER,
        [_edge(module.ALTERNATE_CALLER, "0x0079b310", module.OUTER_UPDATE)],
        0,
    )
    batch = _upstream(
        module.BATCH,
        1,
        [
            _edge(module.BATCH, "0x00713112", module.PRIMARY_CALLER),
            _edge(module.BATCH, "0x00713135", module.PRIMARY_CALLER),
            _edge(module.BATCH, "0x007131b5", module.PRIMARY_CALLER),
        ],
    )
    owner = _upstream(
        module.OWNER_FRONTIER,
        2,
        [_edge(module.OWNER_FRONTIER, "0x00715434", module.BATCH)],
    )
    upper = _upstream(
        module.UPPER_CALLER,
        3,
        [_edge(module.UPPER_CALLER, "0x00715602", module.OWNER_FRONTIER)],
        incoming_count=2,
    )
    payload = {
        "format": module.CALLER_FRONTIER_FORMAT,
        "outer_update_anchor": module.OUTER_UPDATE,
        "upstream_depth": 3,
        "direct_callers": [primary, alternate],
        "upstream_candidates": [batch, owner, upper],
    }
    path = tmp_path / "caller_frontier.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return module, path


def test_builds_verified_upper_direct_chain(tmp_path):
    module, path = _fixture(tmp_path)
    report = module.build_vehicle_upper_direct_contract(path)

    assert report["format"] == "SHIFT.VehicleUpperDirectContract/1"
    assert report["closure"]["upper_direct_path"] == "verified"
    assert report["closure"]["path"] == [
        "0x007155e9",
        "0x00715380",
        "0x00713050",
        "0x00794a30",
        "0x00770e80",
    ]
    assert report["closure"]["alternate_direct_caller_still_ownerless"] is True
    assert [row["direct_call_count"] for row in report["chain_edges"]] == [1, 1, 3]
    assert report["chain_edges"][0]["calls"][0]["instruction"] == "0x00715602"
    assert report["chain_edges"][1]["calls"][0]["instruction"] == "0x00715434"
    assert [edge["instruction"] for edge in report["chain_edges"][2]["calls"]] == [
        "0x00713112",
        "0x00713135",
        "0x007131b5",
    ]
    assert report["instruction_export_addresses"] == ["0x007155e9"]
    assert report["scope"]["direct_call_edges_are_ownership_proof"] is False
    assert report["scope"]["callgraph_depth_is_scheduler_proof"] is False

    candidates = {row["address"]: row for row in report["candidates"]}
    assert candidates["0x007155e9"]["evidence_state"] == "inferred"
    assert candidates["0x007155e9"]["read_offsets"] == []
    assert candidates["0x007155e9"]["write_offsets"] == []
    assert "0x00715602" in candidates["0x007155e9"]["exact_instruction_or_pcode_evidence"]


def test_fails_closed_when_frontier_depth_is_too_shallow(tmp_path):
    module, path = _fixture(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["upstream_depth"] = 2
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="upstream-depth >= 3"):
        module.build_vehicle_upper_direct_contract(path)


def test_fails_closed_when_upper_edge_disappears(tmp_path):
    module, path = _fixture(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["upstream_candidates"][2]["ordered_direct_calls"] = []
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="expected 1 direct call"):
        module.build_vehicle_upper_direct_contract(path)


def test_fails_closed_when_batch_call_count_changes(tmp_path):
    module, path = _fixture(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["upstream_candidates"][0]["ordered_direct_calls"] = payload[
        "upstream_candidates"
    ][0]["ordered_direct_calls"][:2]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="expected 3 direct call"):
        module.build_vehicle_upper_direct_contract(path)


def test_fails_closed_if_alternate_branch_gets_direct_owner(tmp_path):
    module, path = _fixture(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["direct_callers"][1]["direct_incoming_count"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="split frontier must be re-audited"):
        module.build_vehicle_upper_direct_contract(path)


def test_fails_closed_on_input_format_drift(tmp_path):
    module, path = _fixture(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["format"] = "SHIFT.GhidraVehicleOuterUpdateCallerFrontier/999"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=module.CALLER_FRONTIER_FORMAT):
        module.build_vehicle_upper_direct_contract(path)

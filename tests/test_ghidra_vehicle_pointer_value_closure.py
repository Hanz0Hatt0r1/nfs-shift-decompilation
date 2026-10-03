import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_vehicle_pointer_value_closure.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_pointer_value_closure", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _source(kind, instruction, base, displacement):
    return {
        "kind": kind,
        "instruction": instruction,
        "base_register": base,
        "displacement": displacement,
        "displacement_hex": f"0x{displacement:x}",
    }


def _entry(register="ECX"):
    return {
        "kind": "function-entry-register",
        "register": register,
        "abi_role_candidate": "thiscall-receiver" if register == "ECX" else None,
    }


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fixture(tmp_path, *, parent_source=None, transfer_next=None):
    module = _load_module()
    child = "0x00715700"
    parent = "0x00715000"
    grandparent = "0x00714000"
    receiver_call = "0x00715730"
    parent_call = "0x00715050"
    receiver_source = _source("register-relative-load", "0x00715720", "ESI", 0x40)

    receiver = {
        "format": module.RECEIVER_FORMAT,
        "callee": module.UPPER_CALLER,
        "callsites": [
            {
                "caller": child,
                "call_instruction": receiver_call,
                "abi_receiver_register_candidate": "ECX",
                "receiver_definition_trace": {
                    "evidence_state": "verified",
                    "source": receiver_source,
                },
            }
        ],
    }
    receiver_path = _write(tmp_path / "receiver.json", receiver)

    pointer = {
        "format": module.POINTER_FORMAT,
        "upper_caller": module.UPPER_CALLER,
        "origins": [
            {
                "caller": child,
                "call_instruction": receiver_call,
                "receiver_source": receiver_source,
                "base_origin_trace": {
                    "evidence_state": "inferred",
                    "source": _entry("ECX"),
                },
                "direct_incoming_callers": [parent],
                "vtable_store_overlaps": [],
            }
        ],
        "next_instruction_export_addresses": [parent],
    }
    pointer_path = _write(tmp_path / "pointer.json", pointer)

    if parent_source is None:
        parent_source = _source("register-relative-load", "0x00715020", "EDI", 0x20)
    transfer = {
        "format": module.TRANSFER_FORMAT,
        "transfers": [
            {
                "parent": parent,
                "child": child,
                "call_instruction": parent_call,
                "entry_register": "ECX",
                "register_transfer_state": "verified",
                "parent_register_source_trace": {
                    "evidence_state": "verified" if parent_source.get("kind") != "function-entry-register" else "inferred",
                    "source": parent_source,
                },
            }
        ],
        "next_instruction_export_addresses": list(transfer_next or []),
    }
    transfer_path = _write(tmp_path / "transfer.json", transfer)
    return {
        "module": module,
        "child": child,
        "parent": parent,
        "grandparent": grandparent,
        "receiver_call": receiver_call,
        "parent_call": parent_call,
        "receiver": receiver_path,
        "pointer": pointer_path,
        "transfer": transfer_path,
    }


def test_composes_receiver_pointer_and_parent_transfer_chain(tmp_path):
    fx = _fixture(tmp_path)
    report = fx["module"].build_vehicle_pointer_value_closure(
        fx["receiver"], fx["pointer"], [fx["transfer"]]
    )
    assert report["format"] == "SHIFT.VehiclePointerValueClosure/1"
    assert report["node_count"] == 5
    assert report["edge_count"] == 4
    assert report["cycle_count"] == 0
    assert report["source_conflict_count"] == 0
    assert report["current_frontier_addresses"] == []
    assert report["weakest_graph_evidence_state"] == "inferred"
    relations = [edge["relation"] for edge in report["edges"]]
    assert relations.count("receiver-source-to-callsite-register") == 1
    assert relations.count("base-origin-to-receiver-source") == 1
    assert relations.count("call-boundary-register-transfer") == 1
    assert relations.count("parent-source-to-callsite-register") == 1
    assert report["static_endpoint_count"] == 1
    endpoint = report["static_endpoints"][0]
    assert endpoint["kind"] == "register-relative-load"
    assert endpoint["function"] == fx["parent"]
    assert endpoint["semantic_identity_proven"] is False
    assert report["scope"]["graph_connectivity_is_object_identity_proof"] is False


def test_unconsumed_pointer_target_remains_current_frontier(tmp_path):
    fx = _fixture(tmp_path)
    report = fx["module"].build_vehicle_pointer_value_closure(
        fx["receiver"], fx["pointer"], []
    )
    assert report["current_frontier_addresses"] == [fx["parent"]]
    assert report["analyzed_parent_functions"] == []


def test_recursive_transfer_consumes_grandparent_target(tmp_path):
    fx = _fixture(
        tmp_path,
        parent_source=_entry("ECX"),
        transfer_next=["0x00714000"],
    )
    module = fx["module"]
    grandparent_transfer = {
        "format": module.TRANSFER_FORMAT,
        "transfers": [
            {
                "parent": fx["grandparent"],
                "child": fx["parent"],
                "call_instruction": "0x00714050",
                "entry_register": "ECX",
                "register_transfer_state": "verified",
                "parent_register_source_trace": {
                    "evidence_state": "verified",
                    "source": _source(
                        "register-relative-address",
                        "0x00714020",
                        "EBX",
                        0x60,
                    ),
                },
            }
        ],
        "next_instruction_export_addresses": [],
    }
    second = _write(tmp_path / "transfer2.json", grandparent_transfer)
    report = module.build_vehicle_pointer_value_closure(
        fx["receiver"], fx["pointer"], [fx["transfer"], second]
    )
    assert report["current_frontier_addresses"] == []
    assert report["analyzed_parent_functions"] == [fx["grandparent"], fx["parent"]]
    assert report["edge_count"] == 6
    assert any(
        edge["relation"] == "call-boundary-register-transfer"
        and fx["grandparent"] in edge["from"]
        for edge in report["edges"]
    )


def test_duplicate_transfer_report_is_idempotent(tmp_path):
    fx = _fixture(tmp_path)
    report = fx["module"].build_vehicle_pointer_value_closure(
        fx["receiver"], fx["pointer"], [fx["transfer"], fx["transfer"]]
    )
    assert report["node_count"] == 5
    assert report["edge_count"] == 4
    assert report["source_conflict_count"] == 0


def test_conflicting_sources_for_same_parent_callsite_are_ambiguous(tmp_path):
    fx = _fixture(tmp_path)
    module = fx["module"]
    payload = json.loads(fx["transfer"].read_text(encoding="utf-8"))
    payload["transfers"][0]["parent_register_source_trace"] = {
        "evidence_state": "verified",
        "source": _source("register-relative-load", "0x00715024", "EBX", 0x30),
    }
    second = _write(tmp_path / "transfer-conflict.json", payload)
    report = module.build_vehicle_pointer_value_closure(
        fx["receiver"], fx["pointer"], [fx["transfer"], second]
    )
    assert report["source_conflict_count"] == 1
    conflict = report["source_conflicts"][0]
    assert conflict["evidence_state"] == "ambiguous"
    assert len(conflict["sources"]) == 2
    assert any(row["id"] == "multiple-static-sources-for-one-callsite-register" for row in report["blockers"])


def test_cycle_is_reported_not_collapsed(tmp_path):
    fx = _fixture(tmp_path, parent_source=_entry("ECX"))
    module = fx["module"]
    payload = json.loads(fx["transfer"].read_text(encoding="utf-8"))
    payload["transfers"][0]["parent"] = fx["child"]
    payload["transfers"][0]["child"] = fx["child"]
    payload["transfers"][0]["call_instruction"] = fx["receiver_call"]
    cycle_transfer = _write(tmp_path / "transfer-cycle.json", payload)
    report = module.build_vehicle_pointer_value_closure(
        fx["receiver"], fx["pointer"], [cycle_transfer]
    )
    assert report["cycle_count"] == 1
    assert report["cycles"]
    assert any(row["id"] == "pointer-provenance-cycle" for row in report["blockers"])
    assert report["scope"]["cycles_are_not_silently_collapsed"] is True


def test_heuristic_vtable_overlap_stays_ambiguous_blocker(tmp_path):
    fx = _fixture(tmp_path)
    pointer = json.loads(fx["pointer"].read_text(encoding="utf-8"))
    pointer["origins"][0]["vtable_store_overlaps"] = [
        {
            "vtable_store_instruction": "0x00715708",
            "base_register": "ESI",
        }
    ]
    _write(fx["pointer"], pointer)
    report = fx["module"].build_vehicle_pointer_value_closure(
        fx["receiver"], fx["pointer"], [fx["transfer"]]
    )
    rows = [row for row in report["blockers"] if row["id"] == "heuristic-vtable-overlap"]
    assert len(rows) == 1
    assert rows[0]["evidence_state"] == "ambiguous"
    assert rows[0]["pointer_alias_proven"] is False


def test_fails_closed_when_pointer_callsite_missing_from_receiver(tmp_path):
    fx = _fixture(tmp_path)
    receiver = json.loads(fx["receiver"].read_text(encoding="utf-8"))
    receiver["callsites"][0]["call_instruction"] = "0x00715799"
    _write(fx["receiver"], receiver)
    with pytest.raises(ValueError, match="absent from receiver provenance"):
        fx["module"].build_vehicle_pointer_value_closure(
            fx["receiver"], fx["pointer"], [fx["transfer"]]
        )


def test_fails_closed_on_transfer_format_drift(tmp_path):
    fx = _fixture(tmp_path)
    payload = json.loads(fx["transfer"].read_text(encoding="utf-8"))
    payload["format"] = "SHIFT.VehicleParentCallsiteTransfer/999"
    _write(fx["transfer"], payload)
    with pytest.raises(ValueError, match=fx["module"].TRANSFER_FORMAT):
        fx["module"].build_vehicle_pointer_value_closure(
            fx["receiver"], fx["pointer"], [fx["transfer"]]
        )

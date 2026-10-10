import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_direct_callee_alias_subset.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_direct_callee_alias_subset_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_direct_callee_alias_subset", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_upstreams(tmp_path, module):
    direct = tmp_path / "direct.json"
    direct.write_text(json.dumps({
        "format": module.DIRECT_FORMAT,
        "ready": True,
        "authority": {"retail_executable_sha256": module.RETAIL_SHA256},
        "selected_slot3": {"hdvehicle_offset": "0x2380"},
        "paths": {
            "fun00755a60": {
                "receiver": "HDVehicle+0x400+slot*0xa80",
                "slot3_receiver": "HDVehicle+0x2380",
                "exact_root_direct_forward": "FUN_00752fc0",
                "leaf_write_offsets": ["+0x5b8", "+0x7d8"],
                "leaf_has_direct_calls": False,
                "target_overlap": False,
            },
            "fun00760b50": {
                "receiver": "HDVehicle+0x2380",
                "exact_root_direct_forward": None,
                "child_receiver_call": "FUN_007ba860 receives [wheel+0x420]",
                "target_overlap": False,
            },
        },
        "call_inventory": {"FUN_00752fc0": []},
    }), encoding="utf-8")

    primary = tmp_path / "primary.json"
    primary.write_text(json.dumps({
        "format": module.PRIMARY_FORMAT,
        "ready": True,
        "authority": {"retail_executable_sha256": module.RETAIL_SHA256},
        "consumer": {
            "function": "FUN_00755950",
            "target_read": "0x00755958 fld qword [EDX+0x538]",
            "writes_overlap_target_0x538_0x53f": False,
            "only_direct_callee": "0x00755983 -> FUN_007555b0",
            "callee_receiver": "0x00755964 ECX=EDX+0x80",
            "exact_wheel_root_forwarded_to_callee": False,
        },
    }), encoding="utf-8")

    child = tmp_path / "child.json"
    child.write_text(json.dumps({
        "format": module.CHILD_FORMAT,
        "ready": True,
        "authority": {"retail_executable_sha256": module.RETAIL_SHA256},
        "callee": {
            "function": "FUN_00755f80",
            "child_pointer_source": "[wheel+0x420]",
            "child_direct_callees": ["FUN_007af0a0", "FUN_007af010"],
            "exact_wheel_root_forwarded_to_direct_callee": False,
            "indirect_call_count": 0,
        },
    }), encoding="utf-8")

    indirect = tmp_path / "indirect.json"
    indirect.write_text(json.dumps({
        "format": module.INDIRECT_FORMAT,
        "ready": True,
        "carrier_set": {"functions": [
            {"name": "FUN_00755950"},
            {"name": "FUN_00755a60"},
            {"name": "FUN_00752fc0"},
            {"name": "FUN_00760b50"},
            {"name": "FUN_00755f80"},
        ]},
        "indirect_surface": {"carrier_indirect_call_edge_count": 0},
        "adjudication": {
            "known_exact_carrier_indirect_call_edge_surface_complete": True,
            "known_exact_carrier_indirect_call_edge_surface_empty": True,
        },
    }), encoding="utf-8")
    return direct, primary, child, indirect


def test_pinned_direct_callee_subset_is_closed_but_global_alias_frontier_is_not():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3DirectCalleeAliasSubsetClosure/1"
    assert data["selected_slot3"]["wheel_receiver"] == "HDVehicle+0x2380"
    assert set(data["exact_root_direct_callees"]) == {"FUN_00755950", "FUN_00752fc0"}
    assert data["exact_root_direct_callees"]["FUN_00755950"]["target_writer_found"] is False
    assert data["exact_root_direct_callees"]["FUN_00752fc0"]["leaf_write_offsets"] == ["+0x5b8", "+0x7d8"]
    a = data["adjudication"]
    assert a["known_direct_callee_exact_root_receiver_count"] == 2
    assert a["known_direct_callee_created_alias_subset_complete"] is True
    assert a["known_direct_callee_selected_target_writer_found"] is False
    assert a["known_direct_callee_exact_root_escape_found"] is False
    assert a["known_direct_callee_callind_found"] is False
    assert a["callee_created_aliases_ruled_out"] is False
    assert a["stored_or_escaped_aliases_ruled_out"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7


def test_nonroot_direct_receivers_stay_distinct_from_selected_wheel_root():
    rows = json.loads(EVIDENCE.read_text(encoding="utf-8"))["nonroot_direct_callee_receivers"]
    by_name = {row["callee"]: row for row in rows}
    assert by_name["FUN_007555b0"]["receiver"] == "wheel+0x80"
    assert by_name["FUN_007555b0"]["reason_not_exact_root"] == "derived interior pointer"
    for name in ("FUN_007ba860", "FUN_007af0a0", "FUN_007af010"):
        assert by_name[name]["receiver"] == "[wheel+0x420]"
        assert by_name[name]["reason_not_exact_root"] == "dereferenced child pointer"


def test_builder_joins_direct_callee_machine_contracts(tmp_path):
    module = load_module()
    direct, primary, child, indirect = write_upstreams(tmp_path, module)
    result = module.build(direct, primary, child, indirect)
    assert result["adjudication"]["known_direct_callee_exact_root_receiver_count"] == 2
    assert result["exact_root_direct_callees"]["FUN_00752fc0"]["direct_call_count"] == 0
    assert result["exact_root_direct_callees"]["FUN_00755950"]["exact_root_forwarded_further"] is False
    assert result["adjudication"]["known_direct_callee_created_alias_subset_complete"] is True


def test_builder_fails_closed_on_leaf_or_receiver_drift(tmp_path):
    module = load_module()
    direct, primary, child, indirect = write_upstreams(tmp_path, module)

    direct_data = json.loads(direct.read_text(encoding="utf-8"))
    direct_data["call_inventory"]["FUN_00752fc0"] = [{"site": "0x00752fd0", "target": "0x00123456"}]
    direct.write_text(json.dumps(direct_data), encoding="utf-8")
    try:
        module.build(direct, primary, child, indirect)
    except ValueError as exc:
        assert "no longer a direct-call leaf" in str(exc)
    else:
        raise AssertionError("leaf-call drift must fail closed")

    direct, primary, child, indirect = write_upstreams(tmp_path, module)
    primary_data = json.loads(primary.read_text(encoding="utf-8"))
    primary_data["consumer"]["callee_receiver"] = "0x00755964 ECX=EDX"
    primary.write_text(json.dumps(primary_data), encoding="utf-8")
    try:
        module.build(direct, primary, child, indirect)
    except ValueError as exc:
        assert "FUN_00755950 direct-callee surface drift" in str(exc)
    else:
        raise AssertionError("callee-receiver drift must fail closed")

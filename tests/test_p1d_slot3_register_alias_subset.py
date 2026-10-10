import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_register_alias_subset.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_register_alias_subset_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_register_alias_subset", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_upstreams(tmp_path, module):
    primary = tmp_path / "primary.json"
    primary.write_text(json.dumps({
        "format": module.PRIMARY_FORMAT,
        "ready": True,
        "authority": {"retail_executable_sha256": module.RETAIL_SHA256},
        "primary_loop": {
            "function": "FUN_00758b50",
            "selected_wheel_materialization": "0x00758ccf ECX=ESI-0x448=HDVehicle+0x400+slot*0xa80",
            "selected_wheel_direct_call": "0x00758d6b -> FUN_00755950",
            "exact_selected_wheel_root_forwarded_to_other_direct_callee": False,
        },
        "consumer": {
            "function": "FUN_00755950",
            "entry_root_copy": "0x00755956 EDX=ECX",
            "target_read": "0x00755958 fld qword [EDX+0x538]",
            "writes_overlap_target_0x538_0x53f": False,
            "exact_wheel_root_forwarded_to_callee": False,
        },
        "adjudication": {
            "primary_loop_exact_wheel_root_one_hop_forwarding_complete": True,
            "primary_loop_exact_wheel_root_only_direct_target_is_FUN_00755950": True,
            "FUN_00755950_exact_wheel_root_does_not_escape_to_direct_callee": True,
        },
    }), encoding="utf-8")

    child = tmp_path / "child.json"
    child.write_text(json.dumps({
        "format": module.CHILD_FORMAT,
        "ready": True,
        "authority": {"retail_executable_sha256": module.RETAIL_SHA256},
        "caller": {
            "function": "FUN_00763570",
            "wheel_seed": "HDVehicle+0x400",
            "stride": "0xa80",
            "iteration_count": 4,
            "slot3_receiver": "HDVehicle+0x2380",
            "callee": "FUN_00755f80",
        },
        "callee": {
            "function": "FUN_00755f80",
            "exact_wheel_root_capture": "ESI=ECX",
            "wheel_root_write_count": 0,
            "wheel_root_stored_or_pushed_after_capture": False,
            "exact_wheel_root_forwarded_to_direct_callee": False,
            "indirect_call_count": 0,
        },
        "adjudication": {
            "slot3_fun00763570_to_fun00755f80_exact_wheel_path_complete": True,
            "fun00755f80_exact_wheel_escape_found": False,
        },
    }), encoding="utf-8")

    indirect = tmp_path / "indirect.json"
    indirect.write_text(json.dumps({
        "format": module.INDIRECT_FORMAT,
        "ready": True,
        "carrier_set": {
            "functions": [
                {"name": "FUN_00758b50"},
                {"name": "FUN_00755950"},
                {"name": "FUN_00755f80"},
            ]
        },
        "indirect_surface": {"carrier_indirect_call_edge_count": 0},
        "adjudication": {
            "sqlite_indirect_call_edge_class_present": True,
            "known_exact_carrier_indirect_call_edge_surface_complete": True,
            "known_exact_carrier_indirect_call_edge_surface_empty": True,
        },
    }), encoding="utf-8")
    return primary, child, indirect


def test_pinned_register_alias_subset_is_closed_but_global_frontier_is_not():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3RegisterAliasSubsetClosure/1"
    assert data["selected_slot3"]["wheel_receiver"] == "HDVehicle+0x2380"
    assert data["register_aliases"]["FUN_00758b50"]["persistent_store_proven"] is False
    assert data["register_aliases"]["FUN_00755950"]["target_is_read_only_in_consumer"] is True
    assert data["register_aliases"]["FUN_00755f80"]["wheel_root_stored_or_pushed_after_capture"] is False
    a = data["adjudication"]
    assert a["machine_proven_register_alias_subset_complete"] is True
    assert a["machine_proven_register_alias_subset_persistent_store_found"] is False
    assert a["machine_proven_register_alias_subset_new_forward_found"] is False
    assert a["machine_proven_register_alias_subset_callind_found"] is False
    assert a["machine_register_alias_storage_ruled_out"] is False
    assert a["callee_created_aliases_ruled_out"] is False
    assert a["stored_or_escaped_aliases_ruled_out"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7


def test_builder_joins_machine_register_and_indirect_surfaces(tmp_path):
    module = load_module()
    primary, child, indirect = write_upstreams(tmp_path, module)
    result = module.build(primary, child, indirect)
    assert result["register_aliases"]["FUN_00758b50"]["known_exact_carrier_callind_edges"] == 0
    assert result["register_aliases"]["FUN_00755950"]["exact_root_forwarded_to_direct_callee"] is False
    assert result["register_aliases"]["FUN_00755f80"]["machine_proven_selected_iteration_receiver"] == "HDVehicle+0x2380"
    assert result["adjudication"]["machine_proven_register_alias_subset_complete"] is True


def test_builder_fails_closed_on_register_or_callind_drift(tmp_path):
    module = load_module()
    primary, child, indirect = write_upstreams(tmp_path, module)

    primary_data = json.loads(primary.read_text(encoding="utf-8"))
    primary_data["consumer"]["entry_root_copy"] = "0x00755956 EAX=ECX"
    primary.write_text(json.dumps(primary_data), encoding="utf-8")
    try:
        module.build(primary, child, indirect)
    except ValueError as exc:
        assert "FUN_00755950 register alias surface drift" in str(exc)
    else:
        raise AssertionError("register drift must fail closed")

    primary, child, indirect = write_upstreams(tmp_path, module)
    indirect_data = json.loads(indirect.read_text(encoding="utf-8"))
    indirect_data["indirect_surface"]["carrier_indirect_call_edge_count"] = 1
    indirect_data["adjudication"]["known_exact_carrier_indirect_call_edge_surface_empty"] = False
    indirect.write_text(json.dumps(indirect_data), encoding="utf-8")
    try:
        module.build(primary, child, indirect)
    except ValueError as exc:
        assert "indirect-call surface drift" in str(exc)
    else:
        raise AssertionError("CALLIND drift must fail closed")

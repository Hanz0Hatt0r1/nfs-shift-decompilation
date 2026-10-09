import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_derived_wheel_storage_handoff.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_derived_wheel_storage_handoff.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_derived_wheel_storage", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_machine_proven_derived_aliases_do_not_persist():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3DerivedWheelStorageHandoff/1"
    assert data["selected_slot3"]["wheel_receiver"] == "HDVehicle+0x2380"
    f63570 = data["derived_aliases"]["FUN_00763570"]
    assert f63570["machine_proven_seed"] == "HDVehicle+0x400"
    assert f63570["machine_proven_stride"] == "0xa80"
    assert f63570["machine_proven_iteration_count"] == 4
    assert f63570["storage_overwritten_after_wheel_loop"] is True
    assert f63570["persistent_store_of_derived_wheel_pointer_found"] is False
    f70e80 = data["derived_aliases"]["FUN_00770e80"]
    assert f70e80["machine_proven_selected_receiver"] == "HDVehicle+0x2380"
    assert f70e80["source_selected_materialization_count"] == 1
    assert f70e80["persistent_store_of_selected_wheel_pointer_found"] is False


def test_global_escape_gates_remain_fail_closed():
    a = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert a["source_visible_machine_proven_derived_wheel_storage_subset_complete"] is True
    assert a["source_visible_machine_proven_derived_wheel_persistent_store_found"] is False
    assert a["source_visible_machine_proven_derived_wheel_new_forward_found"] is False
    assert a["other_derived_alias_storage_ruled_out"] is False
    assert a["machine_register_alias_storage_ruled_out"] is False
    assert a["callee_created_aliases_ruled_out"] is False
    assert a["stored_or_escaped_aliases_ruled_out"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7


def test_synthetic_builder_joins_machine_identity_to_source_storage(monkeypatch, tmp_path):
    m = load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        "void __thiscall FUN_00763570(void *this,double param_1)\n\n{\n"
        "  local_18._4_4_ = (float)((int)this + 0x400);\n"
        "  fVar8 = FUN_00755f80((int)local_18._4_4_);\n"
        "  local_18._4_4_ = (float)((int)local_18._4_4_ + 0xa80);\n"
        "  local_18._4_4_ = (float)local_40;\n"
        "}\n\n"
        "void __thiscall FUN_00770e80(void *this,undefined8 param_1,undefined8 param_2,char param_3)\n\n{\n"
        "  FUN_00760b50((void *)((int)this + 0x2380),*(double *)((int)this + 0xa0),iVar2);\n"
        "}\n\n"
        "void FUN_00000000()\n\n{\n}\n",
        encoding="utf-8",
    )
    direct = tmp_path / "direct.json"
    direct.write_text(json.dumps({
        "format": m.DIRECT_FORMAT,
        "ready": True,
        "selected_slot3": {"hdvehicle_offset": "0x2380"},
        "paths": {"fun00760b50": {"receiver": "HDVehicle+0x2380", "target_overlap": False}},
        "adjudication": {"fun00760b50_selected_target_writer_found": False},
    }), encoding="utf-8")
    child = tmp_path / "child.json"
    child.write_text(json.dumps({
        "format": m.CHILD_FORMAT,
        "ready": True,
        "caller": {
            "function": "FUN_00763570",
            "wheel_seed": "HDVehicle+0x400",
            "stride": "0xa80",
            "iteration_count": 4,
            "slot3_receiver": "HDVehicle+0x2380",
        },
        "adjudication": {
            "fun00755f80_exact_wheel_escape_found": False,
            "fun00755f80_selected_target_writer_found": False,
        },
    }), encoding="utf-8")
    monkeypatch.setattr(m, "sha256", lambda path: m.SOURCE_SHA256)
    result = m.build(source, direct, child)
    assert result["derived_aliases"]["FUN_00763570"]["persistent_store_of_derived_wheel_pointer_found"] is False
    assert result["derived_aliases"]["FUN_00770e80"]["forward_beyond_already_closed_FUN_00760b50_found"] is False

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1a_slot01_wheel_root_materialization_persistence_handoff.py"
PERSISTENCE = ROOT / "evidence/p1d_slot3_16carrier_direct_root_persistence.json"
MATERIALIZATION = ROOT / "evidence/p1d_slot3_machine_wheel_root_materialization_closure.json"
EVIDENCE = ROOT / "evidence/p1a_p13a_slot01_wheel_root_materialization_persistence_handoff.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1a_wheel_root_handoff", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_handoff():
    module = load_tool()
    assert module.build(load(PERSISTENCE), load(MATERIALIZATION)) == load(EVIDENCE)
    assert module.WHEEL_ROOT_CARRIERS == [
        "FUN_00752fc0",
        "FUN_00755950",
        "FUN_00755a60",
        "FUN_00755f80",
        "FUN_00760b50",
    ]


def test_slot0_slot1_geometry_and_consumers_are_exact():
    data = load(EVIDENCE)
    assert data["format"] == "SHIFT.P1A.P13ASlot01WheelRootMaterializationPersistenceHandoff/1"
    assert data["wheel_layout"] == {
        "count": 4,
        "root_offsets": ["+0x400", "+0xe80", "+0x1900", "+0x2380"],
        "stride": "+0xa80",
    }
    slot0, slot1 = data["slot01"]
    assert slot0 == {
        "absolute_target": "HDVehicle+0x938..+0x93f",
        "explicit_consumer": "FUN_00760b50",
        "explicit_consumer_call": "0x00771107",
        "explicit_materialization_site": "0x007710fe",
        "local_target": "+0x538..+0x53f",
        "loop_consumer": "FUN_00755f80",
        "loop_consumer_call": "0x0076360f",
        "slot": 0,
        "wheel_receiver": "HDVehicle+0x400",
    }
    assert slot1 == {
        "absolute_target": "HDVehicle+0x13b8..+0x13bf",
        "explicit_consumer": "FUN_00760b50",
        "explicit_consumer_call": "0x00771125",
        "explicit_materialization_site": "0x0077111c",
        "local_target": "+0x538..+0x53f",
        "loop_consumer": "FUN_00755f80",
        "loop_consumer_call": "0x0076360f",
        "slot": 1,
        "wheel_receiver": "HDVehicle+0xe80",
    }


def test_exact_wheel_root_persistence_is_bounded_and_negative():
    data = load(EVIDENCE)
    p = data["exact_wheel_root_persistence"]
    assert p["carrier_count"] == 5
    assert p["direct_memory_store_count"] == 0
    assert p["direct_push_count"] == 0
    assert p["direct_register_copy_count"] == 1
    assert p["direct_register_copies"] == [
        {
            "address": "0x00755db3",
            "destination": "ecx",
            "function": "FUN_00755a60",
            "operands": "ecx,esi",
        }
    ]
    assert p["new_persistent_gpr_alias_found"] is False
    m = data["materialization_surface"]
    assert m["fun00763570_loop_cursor_storage"] == "stack-local [EBP-0x4]"
    assert m["fun00763570_nonstack_wheel_root_store_found"] is False
    assert m["fun00770e80_wheel_root_nonstack_store_count"] == 0
    assert m["fun00770e80_wheel_root_push_count"] == 0


def test_global_alias_and_slot_gates_remain_fail_closed():
    adj = load(EVIDENCE)["adjudication"]
    assert adj["p13a_slot01_known_wheel_root_materialization_subset_complete"] is True
    assert adj["p13a_slot01_direct_exact_wheel_root_persistence_subset_complete"] is True
    assert adj["p13a_slot01_exact_wheel_root_nonstack_store_found"] is False
    assert adj["p13a_slot01_exact_wheel_root_push_found"] is False
    assert adj["p13a_slot01_exact_wheel_root_new_persistent_gpr_alias_found"] is False
    assert adj["interior_or_child_alias_storage_ruled_out"] is False
    assert adj["reconstructed_wheel_pointers_ruled_out"] is False
    assert adj["runtime_generated_or_copied_pointer_stores_ruled_out"] is False
    assert adj["callbacks_and_indirect_entry_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1a_slot01_direct_root_persistence_handoff.py"
UPSTREAM = ROOT / "evidence" / "p1d_slot3_16carrier_direct_root_persistence.json"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_direct_hdvehicle_root_persistence_handoff.json"

EXPECTED_HDVEHICLE_CARRIERS = [
    "FUN_00758810",
    "FUN_00758b50",
    "FUN_00758fc0",
    "FUN_00763570",
    "FUN_00765c40",
    "FUN_00766510",
    "FUN_007675f0",
    "FUN_007682c0",
    "FUN_00769ef0",
    "FUN_0076d100",
    "FUN_00770e80",
]

EXPECTED_WHEEL_CARRIERS = [
    "FUN_00752fc0",
    "FUN_00755950",
    "FUN_00755a60",
    "FUN_00755f80",
    "FUN_00760b50",
]


def load_tool():
    spec = importlib.util.spec_from_file_location("p1a_direct_root_handoff", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_handoff_from_merged_upstream():
    module = load_tool()
    upstream = load(UPSTREAM)
    committed = load(EVIDENCE)
    assert module.build(upstream) == committed
    assert module.HDVEHICLE_ROOT_CARRIERS == EXPECTED_HDVEHICLE_CARRIERS
    assert module.EXCLUDED_WHEEL_ROOT_CARRIERS == EXPECTED_WHEEL_CARRIERS


def test_handoff_consumes_only_exact_hdvehicle_root_subset():
    data = load(EVIDENCE)
    assert data["format"] == "SHIFT.P1A.P13ADirectHDVehicleRootPersistenceHandoff/1"
    assert data["upstream_contract"] == "SHIFT.P1D.Slot3SixteenCarrierDirectRootPersistence/1"
    scope = data["scope"]
    assert scope["upstream_carrier_count"] == 16
    assert scope["consumed_exact_hdvehicle_root_carrier_count"] == 11
    assert scope["consumed_exact_hdvehicle_root_carriers"] == EXPECTED_HDVEHICLE_CARRIERS
    assert scope["excluded_exact_wheel_root_carrier_count"] == 5
    assert scope["excluded_exact_wheel_root_carriers"] == EXPECTED_WHEEL_CARRIERS
    assert scope["slot0_target"] == "HDVehicle+0x938..+0x93f"
    assert scope["slot1_target"] == "HDVehicle+0x13b8..+0x13bf"
    assert scope["wheel_local_target"] == "+0x538..+0x53f"


def test_direct_root_persistence_closes_only_bounded_pointer_escape_class():
    data = load(EVIDENCE)
    surface = data["direct_exact_hdvehicle_root_value_surface"]
    assert surface["memory_store_count"] == 2
    assert [row["function"] for row in surface["memory_stores"]] == [
        "FUN_00758b50",
        "FUN_00763570",
    ]
    assert all(row["storage"] == "stack-local" for row in surface["memory_stores"])
    assert surface["nonstack_or_unknown_memory_store_count"] == 0
    assert surface["push_count"] == 0
    assert surface["new_gpr_alias_beyond_ecx_receiver_reload_found"] is False
    assert surface["upstream_total_register_copy_count"] == 23
    assert surface["upstream_register_copy_destinations"] == ["ecx"]

    adj = data["adjudication"]
    assert adj["p13a_direct_exact_hdvehicle_root_persistence_subset_complete"] is True
    assert adj["p13a_direct_exact_hdvehicle_root_nonstack_store_found"] is False
    assert adj["p13a_direct_exact_hdvehicle_root_push_found"] is False
    assert adj["p13a_direct_exact_hdvehicle_root_new_gpr_alias_found"] is False

    assert adj["derived_wheel_or_interior_alias_storage_ruled_out"] is False
    assert adj["runtime_generated_or_copied_pointer_stores_ruled_out"] is False
    assert adj["callee_created_aliases_ruled_out"] is False
    assert adj["callbacks_and_indirect_entry_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "evidence" / "p1a_p13a_slot01_same_function_topology_machine_inventory.json"
CLOSURE = ROOT / "evidence" / "p1a_p13a_slot01_same_function_topology_machine_closure.json"
TOOL = ROOT / "tools" / "ghidra" / "inventory_p1a_slot01_same_function_topology.py"

EXPECTED_ADDRESSES = [
    "0x00757318",
    "0x00763570",
    "0x00765850",
    "0x00765aa0",
    "0x00765c40",
    "0x00769520",
    "0x0076b130",
    "0x0076df50",
    "0x00770e80",
    "0x00a705ae",
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_tool():
    spec = importlib.util.spec_from_file_location("p1a_slot01_machine_inventory", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inventory_pins_authority_and_exact_ten_candidates():
    data = load(INVENTORY)
    assert data["format"] == "SHIFT.P1A.P13ASlot01SameFunctionTopologyMachineInventory/1"
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["authority"]["ghidra_sqlite_sha256"] == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert data["scanned_sized_function_count"] == 41538
    assert data["candidate_count"] == 10
    assert [row["function_address"] for row in data["candidates"]] == EXPECTED_ADDRESSES


def test_inventory_records_key_machine_topology_sites():
    data = load(INVENTORY)
    rows = {row["function_address"]: row for row in data["candidates"]}
    assert rows["0x00757318"]["hits"]["0x400"][0]["address"] == "0x00757348"
    assert rows["0x00757318"]["hits"]["0xa80"][0]["address"] == "0x0075733c"
    assert rows["0x00757318"]["hits"]["0x938"][0]["address"] == "0x007576b0"
    assert rows["0x0076b130"]["hits"]["0xa80"][0]["instruction"] == "push   0xa80"
    assert rows["0x00a705ae"]["hits"]["0x400"][0]["address"] == "0x00a705bd"


def test_all_same_function_topology_candidates_are_rejected_but_slots_stay_open():
    data = load(CLOSURE)
    assert data["format"] == "SHIFT.P1A.P13ASlot01SameFunctionTopologyMachineClosure/1"
    assert [row["address"] for row in data["candidate_adjudication"]] == EXPECTED_ADDRESSES
    assert all(row["rejected"] is True for row in data["candidate_adjudication"])
    adj = data["adjudication"]
    assert adj["same_function_wheel_topology_candidate_count"] == 10
    assert adj["same_function_wheel_topology_rejected_count"] == 10
    assert adj["same_function_wheel_topology_subset_complete"] is True
    assert adj["same_function_topology_target_f64_writer_found"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_closure_pins_constructor_destructor_and_runtime_helper_rejections():
    rows = {row["function"]: row for row in load(CLOSURE)["candidate_adjudication"]}
    assert any("FUN_0076b060" in line and "+0x5e0" in line for line in rows["FUN_0076b130"]["evidence"])
    assert any("FUN_007694b0" in line for line in rows["FUN_00769520"]["evidence"])
    assert any("FUN_00755a60" in line and "+0x850" in line for line in rows["FUN_00770e80"]["evidence"])
    assert any("FUN_00760b50" in line and "+0x8b0" in line for line in rows["FUN_00770e80"]["evidence"])
    assert any("FUN_00755f80" in line and "child+0x48" in line for line in rows["FUN_00763570"]["evidence"])


def test_scanner_exact_scalar_matching_does_not_match_substrings():
    module = load_tool()
    assert module.exact_scalar("lea eax,[ecx+0x400]", "0x400") is True
    assert module.exact_scalar("mov eax,0x4000", "0x400") is False
    assert module.exact_scalar("lea eax,[ecx+0xa80]", "0xa80") is True
    assert module.exact_scalar("mov eax,0xa800", "0xa80") is False


def test_remaining_frontier_is_explicit_and_fail_closed():
    data = load(CLOSURE)
    assert len(data["remaining_frontier"]) == 2
    assert any("Interprocedural aliases" in row for row in data["remaining_frontier"])
    assert any("bulk-copy" in row for row in data["remaining_frontier"])
    assert any("interprocedural aliases" in row for row in data["limits"])

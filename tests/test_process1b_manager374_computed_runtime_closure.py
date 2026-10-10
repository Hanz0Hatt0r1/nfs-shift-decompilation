import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/ghidra/build_p1b_manager374_computed_runtime_closure.py"
EVIDENCE = ROOT / "evidence/p1b_manager374_computed_runtime_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_manager374_computed_runtime_closure", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_evidence():
    module = load_module()
    inputs = {name: json.loads((ROOT / path).read_text()) for name, path in module.PATHS.items()}
    built = module.build(inputs)
    assert built == json.loads(EVIDENCE.read_text())


def test_computed_runtime_frontier_is_closed():
    data = json.loads(EVIDENCE.read_text())
    surface = data["surface"]
    gates = data["adjudication"]
    assert surface["original_computed_runtime_path_count"] == 18
    assert surface["direct_write_through_rejected_count"] == 1
    assert surface["returned_pointer_paths_closed_read_only"] == 1
    assert surface["source_only_forwarding_paths_closed"] == 11
    assert surface["receiver_or_destination_forwarding_paths_closed"] == 6
    assert surface["remaining_computed_runtime_path_count"] == 0
    assert gates["computed_runtime_paths_complete"] is True
    assert gates["computed_address_manager_374_writer_surface_complete"] is True
    assert gates["computed_runtime_path_can_establish_manager_374_to_hdvehicle_4330_join"] is False


def test_global_identity_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text())["adjudication"]
    assert gates["escaped_storage_paths_complete"] is False
    assert gates["stack_argument_alias_paths_complete"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7

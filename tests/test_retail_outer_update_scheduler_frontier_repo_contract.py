import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/ghidra/build_retail_outer_update_scheduler_frontier.py"
RUNTIME_PATH = ROOT / "src/physics/physics_system_runtime.py"


def _module():
    spec = importlib.util.spec_from_file_location("retail_scheduler_frontier_repo", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scheduler_frontier_consumes_current_source_backed_physics_manager_contract() -> None:
    module = _module()
    source = RUNTIME_PATH.read_text(encoding="utf-8")
    contract = module._validate_runtime_contract(source)

    assert contract["format"] == "SHIFT.PhysicsManagerRuntime/1"
    assert contract["manager_vtable_symbol"] == "PTR_FUN_00b04524"
    assert contract["source_header"] == "Source/Manager/cPhysicsManager.hpp"
    assert contract["source_backed_functions"] == ["FUN_0070fae0", "FUN_0070f580"]
    assert contract["named_object"] == "Physics Manager"
    assert contract["verified"] is True

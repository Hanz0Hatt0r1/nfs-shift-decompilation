import importlib.util
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "ghidra"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "plan_subsystem_frontier_instructions.py"
        spec = importlib.util.spec_from_file_location(
            "plan_subsystem_frontier_instructions", path
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _frontier():
    return {
        "format": "SHIFT.GhidraSubsystemMethodFrontier/1",
        "source": {"program": "SHIFT.exe", "executable_md5": "abc"},
        "subsystems": {
            "physics": {},
            "vehicle": {},
            "renderer": {},
        },
        "frontier_candidates": [
            {
                "address": "0x0079cd90",
                "ghidra_name": "FUN_0079cd90",
                "method_name": "MWL::Core::PhysicsAllocator::malloc",
                "subsystem": "physics",
                "connected_slice_addresses": ["0x00710860", "0x00750080"],
                "direct_links": [
                    {"direction": "candidate-to-slice"},
                    {"direction": "candidate-to-slice"},
                ],
                "frontier_candidate": True,
                "promoted": False,
                "calling_convention": "__thiscall",
                "size": 116,
                "mnemonic_sha256": "a" * 64,
            },
            {
                "address": "0x0079ce30",
                "ghidra_name": "FUN_0079ce30",
                "method_name": "MWL::Core::PhysicsAllocator::free",
                "subsystem": "physics",
                "connected_slice_addresses": ["0x00710860"],
                "direct_links": [
                    {"direction": "candidate-to-slice"},
                    {"direction": "candidate-to-slice"},
                    {"direction": "slice-to-candidate"},
                ],
                "frontier_candidate": True,
                "promoted": False,
                "calling_convention": "__thiscall",
                "size": 133,
                "mnemonic_sha256": "b" * 64,
            },
            {
                "address": "0x00799990",
                "ghidra_name": "FUN_00799990",
                "method_name": "MWL::Core::VehicleFactory::Create",
                "subsystem": "vehicle",
                "connected_slice_addresses": ["0x00798df0"],
                "direct_links": [{"direction": "slice-to-candidate"}],
                "frontier_candidate": True,
                "promoted": False,
                "calling_convention": "__cdecl",
                "size": 32,
                "mnemonic_sha256": "c" * 64,
            },
            {
                "address": "0x00850000",
                "ghidra_name": "FUN_00850000",
                "method_name": "MWL::Renderer::IgnoredPromoted",
                "subsystem": "renderer",
                "connected_slice_addresses": ["0x00854e70"],
                "direct_links": [{"direction": "candidate-to-slice"}],
                "frontier_candidate": True,
                "promoted": True,
            },
        ],
    }


def test_builds_deterministic_plan_and_keeps_semantics_unpromoted(monkeypatch, tmp_path):
    module = _load_module()
    monkeypatch.setattr(module, "build_subsystem_method_frontier", lambda root: _frontier())

    report = module.build_instruction_plan(tmp_path, max_targets=8)
    assert report["format"] == "SHIFT.GhidraSubsystemFrontierInstructionPlan/1"
    assert report["eligible_candidate_count"] == 3
    assert report["selected_target_count"] == 3
    assert report["omitted_target_count"] == 0
    assert report["targets"] == [
        "0x0079cd90",
        "0x0079ce30",
        "0x00799990",
    ]
    first = report["selections"][0]
    assert first["method_name"] == "MWL::Core::PhysicsAllocator::malloc"
    assert first["connected_slice_count"] == 2
    assert first["direct_link_count"] == 2
    assert first["direct_link_directions"] == ["candidate-to-slice"]
    assert all(row["promoted"] is False for row in report["selections"])
    assert report["scope"]["selection_is_semantic_promotion"] is False
    assert report["scope"]["instruction_semantics_proven"] is False


def test_filters_subsystem_and_caps_batch(monkeypatch, tmp_path):
    module = _load_module()
    monkeypatch.setattr(module, "build_subsystem_method_frontier", lambda root: _frontier())

    report = module.build_instruction_plan(
        tmp_path,
        subsystems=["physics", "physics"],
        max_targets=1,
    )
    assert report["requested_subsystems"] == ["physics"]
    assert report["eligible_candidate_count"] == 2
    assert report["selected_target_count"] == 1
    assert report["omitted_target_count"] == 1
    assert report["targets"] == ["0x0079cd90"]


def test_unknown_subsystem_and_invalid_limit_fail_closed(monkeypatch, tmp_path):
    module = _load_module()
    monkeypatch.setattr(module, "build_subsystem_method_frontier", lambda root: _frontier())

    try:
        module.build_instruction_plan(tmp_path, subsystems=["audio"])
    except ValueError as exc:
        assert "unknown subsystem" in str(exc)
    else:
        raise AssertionError("unknown subsystem must fail")

    try:
        module.build_instruction_plan(tmp_path, max_targets=0)
    except ValueError as exc:
        assert "max_targets" in str(exc)
    else:
        raise AssertionError("zero-sized instruction batch must fail")

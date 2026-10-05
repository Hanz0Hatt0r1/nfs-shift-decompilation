from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "native_runtime/include/shift_phase715_persistent_vehicle_runtime_wiring.hpp"
INJECTION = ROOT / "native_runtime/include/shift_phase648_runtime_injection.hpp"
PHASE649 = ROOT / "native_runtime/cmake/phase649.cmake"
PHASE715 = ROOT / "native_runtime/cmake/phase715.cmake"
RUNTIME = ROOT / "native_runtime/src/shift_runtime.cpp"
CHECK = ROOT / "native_runtime/tests/persistent_vehicle_runtime_wiring_check.cpp"


def test_phase715_declares_narrow_persistent_renderer_consumer() -> None:
    source = HEADER.read_text(encoding="utf-8")
    assert '"SHIFT.PersistentVehicleRuntimeWiring/1"' in source
    assert '#include "shift_persistent_vehicle_vulkan_upload.hpp"' in source
    assert '#include "shift_phase648_runtime_vehicle_vulkan_wiring.hpp"' in source
    assert "publish_persistent_bmw_vehicle_world_transform_for_render" in source
    assert "upload_current_bmw_vehicle_world_transform_to_vulkan" in source
    assert "renderer_transform_producer_claimed" in source
    assert "test_motion_script_used" in source
    assert "vkMapMemory" not in source
    assert "commit_bmw_vehicle_world_transform(" not in source
    assert "execute_explicit_outer_update(" not in source


def test_phase715_reuses_authoritative_scene_and_phase649_freshness_gates() -> None:
    source = HEADER.read_text(encoding="utf-8")
    assert 'root / "bundle_set.groups"' in source
    assert "phase648_detail::load_scene_paths" in source
    assert "phase648_detail::load_object_geometry" in source
    assert "vehicle_draw_indices(wiring.groups)" in source
    assert "state.commit_generation <= wiring.last_published_commit_generation" in source
    assert "wiring.published_state.commit_generation <=" in source
    assert "wiring.last_uploaded_commit_generation" in source
    assert "kRuntimeVehicleWorldTransformScriptEnv" in source
    assert "cannot both drive vehicle rendering" in source


def test_phase715_is_attached_to_the_one_real_fixed_step_before_phase648_script() -> None:
    injection = INJECTION.read_text(encoding="utf-8")
    runtime = RUNTIME.read_text(encoding="utf-8")
    assert '#include "shift_phase715_persistent_vehicle_runtime_wiring.hpp"' in injection
    phase715 = injection.index("phase715_after_fixed_step(")
    phase648 = injection.index("phase648_after_fixed_step(")
    assert phase715 < phase648
    assert "native_state, simulation_steps" in injection
    assert runtime.count("native_state.fixed_step(intent);") == 1


def test_phase715_build_chain_and_real_vulkan_regression_are_registered() -> None:
    phase649 = PHASE649.read_text(encoding="utf-8")
    phase715 = PHASE715.read_text(encoding="utf-8")
    check = CHECK.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase715.cmake)" in phase649
    assert "shift_runtime_persistent_vehicle_runtime_wiring_check" in phase715
    assert "persistent_vehicle_runtime_wiring_check.cpp" in phase715
    assert "Vulkan::Vulkan" in phase715
    assert "phase715_after_fixed_step(" in check
    assert "publish_persistent_bmw_vehicle_world_transform_for_render" in check
    assert "unrefreshed_generation_rejected" in check
    assert "phase706_freshness_preserved" in check
    assert "script_conflict_rejected_before_gpu" in check
    assert "test_motion_script_required" in check
    assert "retail_transform_producer_claimed" in check

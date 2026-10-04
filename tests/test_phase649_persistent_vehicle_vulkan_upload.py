from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase649_reads_phase706_before_gpu_side_effects():
    source = (ROOT / "native_runtime/src/persistent_vehicle_vulkan_upload.cpp").read_text(
        encoding="utf-8"
    )
    read_pos = source.index("read_current_bmw_vehicle_world_transform")
    wait_pos = source.index("wait_for_all_frame_fences(device, fences, fence_count)")
    upload_pos = source.index("upload_live_vehicle_vertex_buffers")
    assert read_pos < wait_pos < upload_pos
    assert "Stale BODY provenance must fail before any fence wait" in source


def test_phase649_reuses_existing_phase647_and_phase706_contracts():
    header = (ROOT / "native_runtime/include/shift_persistent_vehicle_vulkan_upload.hpp").read_text(
        encoding="utf-8"
    )
    source = (ROOT / "native_runtime/src/persistent_vehicle_vulkan_upload.cpp").read_text(
        encoding="utf-8"
    )
    assert '"SHIFT.PersistentVehicleVulkanUpload/1"' in header
    assert '#include "shift_live_vehicle_vertex_buffer_upload.hpp"' in header
    assert '#include "shift_persistent_bmw_vehicle_world_transform.hpp"' in header
    assert "read_current_bmw_vehicle_world_transform" in source
    assert "upload_live_vehicle_vertex_buffers" in source
    assert "vkMapMemory" not in source
    assert "vkUnmapMemory" not in source


def test_phase649_waits_all_in_flight_fences():
    source = (ROOT / "native_runtime/src/persistent_vehicle_vulkan_upload.cpp").read_text(
        encoding="utf-8"
    )
    assert "vkWaitForFences" in source
    assert "VK_TRUE" in source
    assert "fence_count == 0u" in source
    assert "null frame fence" in source


def test_phase649_is_chained_after_merged_phase648():
    phase648 = (ROOT / "native_runtime/cmake/phase648.cmake").read_text(encoding="utf-8")
    phase649 = (ROOT / "native_runtime/cmake/phase649.cmake").read_text(encoding="utf-8")
    assert "shift_phase648_runtime_injection.hpp" in phase648
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase649.cmake)" in phase648
    assert "persistent_vehicle_vulkan_upload.cpp" in phase649
    assert "persistent_vehicle_vulkan_upload_check.cpp" in phase649
    assert "Vulkan::Vulkan" in phase649


def test_phase649_real_vulkan_regression_is_fail_closed():
    check = (ROOT / "native_runtime/tests/persistent_vehicle_vulkan_upload_check.cpp").read_text(
        encoding="utf-8"
    )
    assert "upload_current_bmw_vehicle_world_transform_to_vulkan" in check
    assert "VK_FENCE_CREATE_SIGNALED_BIT" in check
    assert "stale_generation_rejected" in check
    assert "changed_pose_rejected" in check
    assert "stale-generation rejection mutated Vulkan memory" in check
    assert "changed-pose rejection mutated Vulkan memory" in check
    assert "Phase 649 mutated track Vulkan memory" in check
    assert "real_vulkan_memory_upload" in check

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "native_runtime/include/shift_phase648_runtime_vehicle_vulkan_wiring.hpp"
INJECTION = ROOT / "native_runtime/include/shift_phase648_runtime_injection.hpp"
PHASE_CMAKE = ROOT / "native_runtime/cmake/phase648.cmake"
PHASE706_CMAKE = ROOT / "native_runtime/cmake/phase706.cmake"
RUNTIME = ROOT / "native_runtime/src/shift_runtime.cpp"


def test_phase648_delegates_gpu_writes_to_merged_phase647_primitive():
    source = ADAPTER.read_text(encoding="utf-8")

    assert '#include "shift_live_vehicle_vertex_buffer_upload.hpp"' in source
    assert "upload_live_vehicle_vertex_buffers(" in source
    assert "kLiveVehicleVertexBufferUploadFormat" in source
    assert "vkMapMemory" not in source
    assert "vkUnmapMemory" not in source


def test_phase648_synchronizes_all_in_flight_frames_before_upload():
    source = ADAPTER.read_text(encoding="utf-8")

    wait = source.index("vkWaitForFences(")
    upload = source.index("upload_live_vehicle_vertex_buffers(")
    assert wait < upload
    assert "runtime.fences.size()" in source
    assert "VK_TRUE" in source
    assert "std::numeric_limits<std::uint64_t>::max()" in source
    assert '"all_frame_fences_waited\\\":true"' in source


def test_phase648_reloads_immutable_object_space_geometry_and_exact_groups():
    source = ADAPTER.read_text(encoding="utf-8")

    assert 'root / "bundle_set.groups"' in source
    assert 'root / "bundle_set.paths"' in source
    assert 'bundle_root / "geometry.svpk"' in source
    assert 'std::memcmp(header.magic, "SVGP", 4u)' in source
    assert "header.version != 3u" in source
    assert "vehicle_draw_indices(wiring.groups)" in source
    assert "object.vertex_bytes.size() != startup.vertex_bytes.size()" in source
    assert '"object_space_reapply\\\":true"' in source


def test_phase648_runtime_attachment_is_explicit_and_fail_closed():
    adapter = ADAPTER.read_text(encoding="utf-8")
    injection = INJECTION.read_text(encoding="utf-8")
    runtime = RUNTIME.read_text(encoding="utf-8")

    assert "SHIFT_NATIVE_VEHICLE_WORLD_TRANSFORM_SCRIPT" in adapter
    assert "if (script_path == nullptr || *script_path == '\\0')" in adapter
    assert "retail_producer_claimed" in adapter
    assert "phase706_snapshot_abi_compatible" in adapter
    assert '#include "../src/runtime_state.hpp"' in injection
    assert "#define fixed_step(phase648_intent_)" in injection
    assert "phase648_after_fixed_step(" in injection
    assert runtime.count("native_state.fixed_step(intent);") == 1


def test_phase648_build_chain_registers_existing_sources_without_new_uploader():
    cmake = PHASE_CMAKE.read_text(encoding="utf-8")
    phase706 = PHASE706_CMAKE.read_text(encoding="utf-8")

    assert "src/vehicle_world_transform_transport.cpp" in cmake
    assert "src/live_vehicle_vertex_buffer_upload.cpp" in cmake
    assert "shift_phase648_runtime_injection.hpp" in cmake
    assert "phase648.cmake" in phase706
    assert not (ROOT / "native_runtime/src/phase648_live_vehicle_vertex_buffer_upload.cpp").exists()


def test_phase648_emits_runtime_wiring_and_upload_telemetry():
    source = ADAPTER.read_text(encoding="utf-8")

    assert "SHIFT.RuntimeVehicleVulkanWiring/1" in source
    assert "SHIFT.RuntimeVehicleVulkanUpload/1" in source
    assert '"source\\\":\\\"phase646-script-regression\\\""' in source
    assert '"track_draw_writes\\\":0"' in source

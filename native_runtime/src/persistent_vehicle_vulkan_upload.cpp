#include "shift_persistent_vehicle_vulkan_upload.hpp"

#include "runtime_state.hpp"

#include <limits>
#include <stdexcept>

namespace shift::runtime::render {
namespace {

void wait_for_all_frame_fences(
    VkDevice device,
    const VkFence* fences,
    std::size_t fence_count) {
    if (device == VK_NULL_HANDLE) {
        throw std::invalid_argument(
            "Phase 649 persistent vehicle upload requires a Vulkan device");
    }
    if (fences == nullptr || fence_count == 0u ||
        fence_count > static_cast<std::size_t>(
            std::numeric_limits<std::uint32_t>::max())) {
        throw std::invalid_argument(
            "Phase 649 persistent vehicle upload requires a finite non-empty fence set");
    }
    for (std::size_t index = 0u; index < fence_count; ++index) {
        if (fences[index] == VK_NULL_HANDLE) {
            throw std::invalid_argument(
                "Phase 649 persistent vehicle upload contains a null frame fence");
        }
    }

    const VkResult result = vkWaitForFences(
        device,
        static_cast<std::uint32_t>(fence_count),
        fences,
        VK_TRUE,
        std::numeric_limits<std::uint64_t>::max());
    if (result != VK_SUCCESS) {
        throw std::runtime_error(
            "Phase 649 vkWaitForFences(all in-flight frames) failed");
    }
}

}  // namespace

PersistentVehicleVulkanUploadResult
upload_current_bmw_vehicle_world_transform_to_vulkan(
    VkDevice device,
    const VkFence* fences,
    std::size_t fence_count,
    const std::vector<std::string>& draw_groups,
    const std::vector<VehicleObjectGeometry>& immutable_object_geometry,
    const std::vector<LiveVehicleVertexBufferTarget>& vertex_targets,
    const shift::runtime::physics::PersistentBmwVehicleWorldTransformState& state,
    const shift::runtime::NativeRuntimeState& runtime) {
    // The Phase 706 freshness read is intentionally the first stateful gate.
    // Stale BODY provenance must fail before any fence wait, memory mapping or
    // live Vulkan vertex write can occur.
    const auto snapshot =
        shift::runtime::physics::read_current_bmw_vehicle_world_transform(
            state,
            runtime);

    wait_for_all_frame_fences(device, fences, fence_count);

    PersistentVehicleVulkanUploadResult result{};
    result.snapshot = snapshot;
    result.upload = upload_live_vehicle_vertex_buffers(
        draw_groups,
        immutable_object_geometry,
        vertex_targets,
        snapshot.vehicle_world_matrix);
    result.all_frame_fences_waited = true;
    return result;
}

}  // namespace shift::runtime::render

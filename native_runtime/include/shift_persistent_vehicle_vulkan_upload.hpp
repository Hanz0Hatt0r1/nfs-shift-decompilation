#pragma once

namespace shift::runtime {
struct NativeRuntimeState;
}

#include "shift_live_vehicle_vertex_buffer_upload.hpp"
#include "shift_persistent_bmw_vehicle_world_transform.hpp"

#include <vulkan/vulkan.h>

#include <cstddef>
#include <string>
#include <vector>

namespace shift::runtime::render {

inline constexpr const char* kPersistentVehicleVulkanUploadFormat =
    "SHIFT.PersistentVehicleVulkanUpload/1";

struct PersistentVehicleVulkanUploadResult {
    shift::runtime::physics::PersistentBmwVehicleWorldTransformSnapshot snapshot{};
    LiveVehicleVertexBufferUploadResult upload{};
    bool all_frame_fences_waited = false;
};

PersistentVehicleVulkanUploadResult
upload_current_bmw_vehicle_world_transform_to_vulkan(
    VkDevice device,
    const VkFence* fences,
    std::size_t fence_count,
    const std::vector<std::string>& draw_groups,
    const std::vector<VehicleObjectGeometry>& immutable_object_geometry,
    const std::vector<LiveVehicleVertexBufferTarget>& vertex_targets,
    const shift::runtime::physics::PersistentBmwVehicleWorldTransformState& state,
    const shift::runtime::NativeRuntimeState& runtime);

}  // namespace shift::runtime::render

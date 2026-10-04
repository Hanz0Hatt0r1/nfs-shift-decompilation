#pragma once

#include "shift_vehicle_world_transform_transport.hpp"

#include <vulkan/vulkan.h>

#include <cstddef>
#include <string>
#include <vector>

namespace shift::runtime::render {

inline constexpr const char* kLiveVehicleVertexBufferUploadFormat =
    "SHIFT.LiveVehicleVertexBufferUpload/1";

struct LiveVehicleVertexBufferTarget {
    VkDevice device = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    std::size_t vertex_payload_bytes = 0u;
};

struct LiveVehicleVertexBufferUploadResult {
    std::vector<std::size_t> vehicle_draw_indices;
    std::size_t uploaded_bytes = 0u;
};

LiveVehicleVertexBufferUploadResult upload_live_vehicle_vertex_buffers(
    const std::vector<std::string>& draw_groups,
    const std::vector<VehicleObjectGeometry>& immutable_object_geometry,
    const std::vector<LiveVehicleVertexBufferTarget>& vertex_targets,
    const VehicleWorldMatrix& vehicle_world_matrix);

}  // namespace shift::runtime::render

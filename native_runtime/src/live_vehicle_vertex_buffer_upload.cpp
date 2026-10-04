#include "shift_live_vehicle_vertex_buffer_upload.hpp"

#include <cstring>
#include <stdexcept>
#include <unordered_set>
#include <utility>

namespace shift::runtime::render {
namespace {

struct PreparedVehicleUpload {
    std::size_t draw_index = 0u;
    VkDevice device = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    std::vector<std::uint8_t> vertex_bytes;
    void* mapped = nullptr;
};

void unmap_prepared(std::vector<PreparedVehicleUpload>& uploads) noexcept {
    for (auto& upload : uploads) {
        if (upload.mapped != nullptr &&
            upload.device != VK_NULL_HANDLE &&
            upload.memory != VK_NULL_HANDLE) {
            vkUnmapMemory(upload.device, upload.memory);
            upload.mapped = nullptr;
        }
    }
}

}  // namespace

LiveVehicleVertexBufferUploadResult upload_live_vehicle_vertex_buffers(
    const std::vector<std::string>& draw_groups,
    const std::vector<VehicleObjectGeometry>& immutable_object_geometry,
    const std::vector<LiveVehicleVertexBufferTarget>& vertex_targets,
    const VehicleWorldMatrix& vehicle_world_matrix) {

    if (draw_groups.size() != immutable_object_geometry.size() ||
        draw_groups.size() != vertex_targets.size()) {
        throw std::invalid_argument(
            "Phase 647 draw groups, immutable geometry and Vulkan targets must have identical counts");
    }

    const std::vector<std::size_t> indices =
        vehicle_draw_indices(draw_groups);
    if (indices.empty()) {
        throw std::invalid_argument(
            "Phase 647 scene contains no authoritative vehicle draws");
    }

    // Phase 646 owns matrix validation and semantic geometry transformation.
    // Prepare every byte payload before mapping any GPU-visible memory so that
    // format/semantic/size failures cannot partially mutate the live scene.
    std::vector<PreparedVehicleUpload> prepared;
    prepared.reserve(indices.size());
    std::unordered_set<VkDeviceMemory> unique_memories;

    for (const std::size_t draw_index : indices) {
        if (draw_index >= immutable_object_geometry.size()) {
            throw std::logic_error(
                "Phase 646 vehicle draw index exceeds Phase 647 geometry count");
        }
        const VehicleObjectGeometry& geometry =
            immutable_object_geometry[draw_index];
        const LiveVehicleVertexBufferTarget& target =
            vertex_targets[draw_index];

        if (geometry.vertex_bytes.empty()) {
            throw std::invalid_argument(
                "Phase 647 vehicle draw has no immutable object-space vertex bytes");
        }
        if (target.device == VK_NULL_HANDLE ||
            target.memory == VK_NULL_HANDLE) {
            throw std::invalid_argument(
                "Phase 647 vehicle draw has no live Vulkan device/memory target");
        }
        if (target.vertex_payload_bytes != geometry.vertex_bytes.size()) {
            throw std::invalid_argument(
                "Phase 647 Vulkan target payload size does not match immutable geometry");
        }
        if (!unique_memories.insert(target.memory).second) {
            throw std::invalid_argument(
                "Phase 647 vehicle draws alias the same Vulkan memory allocation");
        }

        VehicleWorldTransformResult transformed =
            apply_vehicle_world_transform(
                geometry,
                vehicle_world_matrix);
        if (transformed.vertex_bytes.size() !=
            geometry.vertex_bytes.size()) {
            throw std::logic_error(
                "Phase 646 transform changed the vehicle vertex payload size");
        }

        PreparedVehicleUpload upload{};
        upload.draw_index = draw_index;
        upload.device = target.device;
        upload.memory = target.memory;
        upload.vertex_bytes = std::move(transformed.vertex_bytes);
        prepared.push_back(std::move(upload));
    }

    // Map every target first. If one mapping fails, unmap all earlier targets
    // before returning and no vertex bytes have been copied yet.
    for (auto& upload : prepared) {
        const VkResult mapped = vkMapMemory(
            upload.device,
            upload.memory,
            0,
            static_cast<VkDeviceSize>(upload.vertex_bytes.size()),
            0,
            &upload.mapped);
        if (mapped != VK_SUCCESS || upload.mapped == nullptr) {
            unmap_prepared(prepared);
            throw std::runtime_error(
                "Phase 647 vkMapMemory failed for vehicle vertex buffer");
        }
    }

    LiveVehicleVertexBufferUploadResult result{};
    result.vehicle_draw_indices = indices;
    for (auto& upload : prepared) {
        std::memcpy(
            upload.mapped,
            upload.vertex_bytes.data(),
            upload.vertex_bytes.size());
        result.uploaded_bytes += upload.vertex_bytes.size();
    }
    unmap_prepared(prepared);
    return result;
}

}  // namespace shift::runtime::render

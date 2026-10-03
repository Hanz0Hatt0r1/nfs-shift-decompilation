#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace shift::runtime::render {

using VehicleWorldMatrix = std::array<float, 16>;

struct VehicleWorldTransformScript {
    static constexpr const char* format =
        "SHIFT.NativeVehicleWorldTransformScript/1";
    std::vector<VehicleWorldMatrix> steps;
};

struct VehicleVertexAttribute {
    std::uint32_t location = 0;
    std::uint32_t format = 0;
    std::uint32_t offset = 0;
    std::uint32_t stride = 0;
    std::uint32_t property_id = 0;
};

struct VehicleObjectGeometry {
    std::uint32_t stride = 0;
    std::vector<VehicleVertexAttribute> attributes;
    std::vector<std::uint8_t> vertex_bytes;
};

struct VehicleWorldTransformResult {
    std::vector<std::uint8_t> vertex_bytes;
    std::vector<float> positions;
    float determinant = 0.0f;
    bool linear_identity = false;
    std::string mode;
};

VehicleWorldTransformScript load_vehicle_world_transform_script(
    const std::string& path);

std::vector<std::string> load_native_scene_draw_groups(
    const std::string& path,
    std::size_t expected_draw_count);

std::vector<std::size_t> vehicle_draw_indices(
    const std::vector<std::string>& groups);

void validate_vehicle_world_matrix(
    const VehicleWorldMatrix& matrix);

VehicleWorldTransformResult apply_vehicle_world_transform(
    const VehicleObjectGeometry& object_geometry,
    const VehicleWorldMatrix& matrix);

}  // namespace shift::runtime::render

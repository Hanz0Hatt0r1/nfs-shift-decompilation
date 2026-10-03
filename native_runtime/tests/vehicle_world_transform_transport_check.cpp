#include "shift_vehicle_world_transform_transport.hpp"

#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

using namespace shift::runtime::render;

namespace {

void require_close(float actual, float expected, const char* label) {
    if (std::fabs(actual - expected) > 1.0e-5f) {
        throw std::runtime_error(
            std::string(label) + " mismatch: " +
            std::to_string(actual) + " vs " +
            std::to_string(expected));
    }
}

VehicleWorldMatrix translation(float x, float y, float z) {
    return {
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        x, y, z, 1,
    };
}

void append_float3(std::vector<std::uint8_t>& bytes,
                   float x, float y, float z) {
    const float values[3] = {x, y, z};
    const auto* raw = reinterpret_cast<const std::uint8_t*>(values);
    bytes.insert(bytes.end(), raw, raw + sizeof(values));
}

}  // namespace

int main() {
    try {
        VehicleObjectGeometry geometry{};
        geometry.stride = 48u;
        geometry.attributes = {
            {0u, 2u, 0u, 48u, 200u},
            {1u, 2u, 12u, 48u, 220u},
            {2u, 2u, 24u, 48u, 240u},
            {3u, 2u, 36u, 48u, 250u},
        };
        append_float3(geometry.vertex_bytes, 1.0f, 2.0f, 3.0f);
        append_float3(geometry.vertex_bytes, 0.0f, 1.0f, 0.0f);
        append_float3(geometry.vertex_bytes, 1.0f, 0.0f, 0.0f);
        append_float3(geometry.vertex_bytes, 0.0f, 0.0f, 1.0f);

        const auto first = apply_vehicle_world_transform(
            geometry, translation(10.0f, 20.0f, 30.0f));
        require_close(first.positions[0], 11.0f, "first x");
        require_close(first.positions[1], 22.0f, "first y");
        require_close(first.positions[2], 33.0f, "first z");

        // The second transform must start from immutable object-space bytes,
        // not from `first.vertex_bytes`.  This catches cumulative frame drift.
        const auto second = apply_vehicle_world_transform(
            geometry, translation(-4.0f, 5.0f, 0.5f));
        require_close(second.positions[0], -3.0f, "second x");
        require_close(second.positions[1], 7.0f, "second y");
        require_close(second.positions[2], 3.5f, "second z");

        VehicleWorldMatrix affine = {
            0.0f, 2.0f, 0.0f, 0.0f,
            -1.0f, 0.0f, 0.0f, 0.0f,
            0.0f, 0.0f, 0.5f, 0.0f,
            0.1f, 0.2f, 0.3f, 1.0f,
        };
        const auto transformed = apply_vehicle_world_transform(geometry, affine);
        require_close(transformed.positions[0], -1.9f, "affine x");
        require_close(transformed.positions[1], 2.2f, "affine y");
        require_close(transformed.positions[2], 1.8f, "affine z");
        if (transformed.mode != "affine-semantic-v3") {
            throw std::runtime_error("unexpected affine transform mode");
        }

        const auto temp = std::filesystem::temp_directory_path() /
            "shift_phase646_vehicle_transform";
        std::filesystem::create_directories(temp);
        const auto script_path = temp / "vehicle_transform.script";
        {
            std::ofstream script(script_path);
            script << VehicleWorldTransformScript::format << "\n";
            const auto a = translation(0, 0, 0);
            const auto b = translation(1, 2, 3);
            for (std::size_t step = 0; step < 2; ++step) {
                script << step;
                const auto& matrix = step == 0 ? a : b;
                for (float value : matrix) script << ' ' << value;
                script << '\n';
            }
        }
        const auto script = load_vehicle_world_transform_script(
            script_path.string());
        if (script.steps.size() != 2u || script.steps[1][12] != 1.0f ||
            script.steps[1][13] != 2.0f || script.steps[1][14] != 3.0f) {
            throw std::runtime_error("vehicle transform script parse mismatch");
        }

        const auto groups_path = temp / "bundle_set.groups";
        {
            std::ofstream groups(groups_path);
            groups << "track\ntrack\nvehicle\nvehicle\n";
        }
        const auto groups = load_native_scene_draw_groups(
            groups_path.string(), 4u);
        const auto indices = vehicle_draw_indices(groups);
        if (indices.size() != 2u || indices[0] != 2u || indices[1] != 3u) {
            throw std::runtime_error("vehicle draw-group selection mismatch");
        }

        bool singular_rejected = false;
        try {
            auto bad = translation(0, 0, 0);
            bad[0] = 0.0f;
            validate_vehicle_world_matrix(bad);
        } catch (const std::runtime_error&) {
            singular_rejected = true;
        }
        if (!singular_rejected) {
            throw std::runtime_error("singular dynamic transform was accepted");
        }

        std::filesystem::remove_all(temp);
        std::cout
            << "{\"format\":\"SHIFT.NativeVehicleWorldTransformTransportCheck/1\","
            << "\"ready\":true,"
            << "\"non_cumulative_reapply\":true,"
            << "\"vehicle_draw_count\":2}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "vehicle_world_transform_transport_check: "
                  << error.what() << '\n';
        return 1;
    }
}

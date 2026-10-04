#pragma once

#include "shift_live_vehicle_vertex_buffer_upload.hpp"

#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace shift::runtime::render {

inline constexpr const char* kRuntimeVehicleVulkanWiringFormat =
    "SHIFT.RuntimeVehicleVulkanWiring/1";
inline constexpr const char* kRuntimeVehicleVulkanUploadFormat =
    "SHIFT.RuntimeVehicleVulkanUpload/1";
inline constexpr const char* kRuntimeVehicleWorldTransformScriptEnv =
    "SHIFT_NATIVE_VEHICLE_WORLD_TRANSFORM_SCRIPT";

namespace phase648_detail {

#pragma pack(push, 1)
struct GeometryHeader {
    char magic[4];
    std::uint32_t version;
    std::uint32_t vertex_count;
    std::uint32_t index_count;
    std::uint32_t stride;
    std::uint32_t attribute_count;
    std::uint32_t first_index;
    float center_x;
    float center_y;
    float center_z;
    float scale;
};

struct GeometryAttribute {
    std::uint32_t location;
    std::uint32_t format;
    std::uint32_t offset;
    std::uint32_t stride;
    std::uint32_t property_id;
};
#pragma pack(pop)

static_assert(sizeof(GeometryHeader) == 44u);
static_assert(sizeof(GeometryAttribute) == 20u);

inline std::vector<std::uint8_t> read_bytes(
    const std::filesystem::path& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) {
        throw std::runtime_error(
            "Phase 648 cannot open geometry packet: " + path.string());
    }
    const std::streamsize size = file.tellg();
    if (size <= 0) {
        throw std::runtime_error(
            "Phase 648 geometry packet is empty: " + path.string());
    }
    file.seekg(0);
    std::vector<std::uint8_t> bytes(static_cast<std::size_t>(size));
    if (!file.read(reinterpret_cast<char*>(bytes.data()), size)) {
        throw std::runtime_error(
            "Phase 648 cannot read geometry packet: " + path.string());
    }
    return bytes;
}

inline std::vector<std::filesystem::path> load_scene_paths(
    const std::filesystem::path& root,
    std::size_t expected_count) {
    std::ifstream file(root / "bundle_set.paths");
    if (!file) {
        throw std::runtime_error(
            "Phase 648 scene is missing bundle_set.paths");
    }

    std::vector<std::filesystem::path> paths;
    std::string line;
    while (std::getline(file, line)) {
        const auto first = line.find_first_not_of(" \t\r\n");
        if (first == std::string::npos) {
            continue;
        }
        const auto last = line.find_last_not_of(" \t\r\n");
        const std::filesystem::path relative(
            line.substr(first, last - first + 1u));
        if (relative.is_absolute()) {
            throw std::runtime_error(
                "Phase 648 scene path must be relative");
        }
        for (const auto& part : relative) {
            if (part == "..") {
                throw std::runtime_error(
                    "Phase 648 scene path escapes scene root");
            }
        }
        paths.push_back((root / relative).lexically_normal());
    }

    if (paths.size() != expected_count) {
        throw std::runtime_error(
            "Phase 648 bundle_set.paths count mismatch");
    }
    return paths;
}

inline VehicleObjectGeometry load_object_geometry(
    const std::filesystem::path& bundle_root) {
    const auto bytes = read_bytes(bundle_root / "geometry.svpk");
    if (bytes.size() < sizeof(GeometryHeader)) {
        throw std::runtime_error("Phase 648 SVGP header is truncated");
    }

    GeometryHeader header{};
    std::memcpy(&header, bytes.data(), sizeof(header));
    if (std::memcmp(header.magic, "SVGP", 4u) != 0 ||
        header.version != 3u) {
        throw std::runtime_error(
            "Phase 648 dynamic vehicle geometry requires semantic SVGP v3");
    }
    if (header.vertex_count == 0u || header.index_count == 0u ||
        header.stride == 0u || header.attribute_count == 0u ||
        header.attribute_count > 16u) {
        throw std::runtime_error("Phase 648 SVGP header shape is invalid");
    }

    const std::size_t attributes_bytes =
        static_cast<std::size_t>(header.attribute_count) *
        sizeof(GeometryAttribute);
    const std::size_t vertex_bytes =
        static_cast<std::size_t>(header.vertex_count) * header.stride;
    const std::size_t index_bytes =
        static_cast<std::size_t>(header.index_count) * sizeof(std::uint32_t);
    const std::size_t vertex_base = sizeof(GeometryHeader) + attributes_bytes;
    const std::size_t index_base = vertex_base + vertex_bytes;
    if (index_base + index_bytes != bytes.size()) {
        throw std::runtime_error("Phase 648 SVGP packet size mismatch");
    }

    VehicleObjectGeometry geometry{};
    geometry.stride = header.stride;
    geometry.attributes.reserve(header.attribute_count);
    for (std::uint32_t index = 0; index < header.attribute_count; ++index) {
        GeometryAttribute raw{};
        std::memcpy(
            &raw,
            bytes.data() + sizeof(GeometryHeader) +
                static_cast<std::size_t>(index) * sizeof(GeometryAttribute),
            sizeof(raw));
        if (raw.stride != header.stride ||
            raw.offset + 3u * sizeof(float) > header.stride) {
            throw std::runtime_error(
                "Phase 648 SVGP attribute exceeds vertex stride");
        }
        geometry.attributes.push_back({
            raw.location,
            raw.format,
            raw.offset,
            raw.stride,
            raw.property_id,
        });
    }
    geometry.vertex_bytes.assign(
        bytes.begin() + static_cast<std::ptrdiff_t>(vertex_base),
        bytes.begin() + static_cast<std::ptrdiff_t>(index_base));
    return geometry;
}

struct RuntimeVehicleWiringState {
    bool environment_checked = false;
    bool enabled = false;
    VehicleWorldTransformScript script{};
    std::vector<std::string> groups;
    std::vector<VehicleObjectGeometry> object_geometries;
    std::vector<LiveVehicleVertexBufferTarget> targets;
    std::vector<std::size_t> vehicle_indices;
    std::uint64_t upload_steps = 0u;
};

inline RuntimeVehicleWiringState& state() {
    static RuntimeVehicleWiringState value{};
    return value;
}

template <typename RuntimeT>
inline void wait_for_all_in_flight_frames(RuntimeT& runtime) {
    if (runtime.device == VK_NULL_HANDLE) {
        throw std::runtime_error(
            "Phase 648 cannot synchronize without a Vulkan device");
    }
    if (runtime.fences.empty()) {
        throw std::runtime_error(
            "Phase 648 runtime has no in-flight fences");
    }
    const VkResult result = vkWaitForFences(
        runtime.device,
        static_cast<std::uint32_t>(runtime.fences.size()),
        runtime.fences.data(),
        VK_TRUE,
        std::numeric_limits<std::uint64_t>::max());
    if (result != VK_SUCCESS) {
        throw std::runtime_error(
            "Phase 648 vkWaitForFences(all frames) failed");
    }
}

}  // namespace phase648_detail

// The current executable has no positive retail BODY-owner/bind producer yet.
// Phase 648 therefore keeps the runtime attachment inert unless the established
// Phase 646 transform-script regression source is explicitly selected.  The
// upload itself is delegated to the merged Phase 647 primitive.
template <typename RuntimeT, typename GeometryVector>
inline void phase648_after_fixed_step(
    RuntimeT& runtime,
    const GeometryVector& startup_geometry,
    const std::string& scene_set,
    bool scene_set_mode,
    std::uint64_t simulation_step,
    int frame_limit) {
    auto& wiring = phase648_detail::state();

    if (!wiring.environment_checked) {
        wiring.environment_checked = true;
        const char* script_path =
            std::getenv(kRuntimeVehicleWorldTransformScriptEnv);
        if (script_path == nullptr || *script_path == '\0') {
            return;
        }
        wiring.enabled = true;

        if (!scene_set_mode || scene_set.empty()) {
            throw std::runtime_error(
                "Phase 648 vehicle Vulkan wiring requires --scene-set");
        }
        if (frame_limit <= 0) {
            throw std::runtime_error("Phase 648 frame limit is invalid");
        }
        if (startup_geometry.size() != runtime.material_draws.size()) {
            throw std::runtime_error(
                "Phase 648 startup geometry/Vulkan draw count mismatch");
        }

        const std::filesystem::path root(scene_set);
        wiring.script = load_vehicle_world_transform_script(script_path);
        if (wiring.script.steps.size() !=
            static_cast<std::size_t>(frame_limit)) {
            throw std::runtime_error(
                "Phase 648 transform script steps must equal runtime frame limit");
        }
        wiring.groups = load_native_scene_draw_groups(
            (root / "bundle_set.groups").string(),
            startup_geometry.size());
        wiring.vehicle_indices = vehicle_draw_indices(wiring.groups);

        const auto paths = phase648_detail::load_scene_paths(
            root, startup_geometry.size());
        wiring.object_geometries.resize(startup_geometry.size());
        wiring.targets.resize(startup_geometry.size());

        for (const std::size_t draw_index : wiring.vehicle_indices) {
            auto object = phase648_detail::load_object_geometry(
                paths.at(draw_index));
            const auto& startup = startup_geometry.at(draw_index);
            if (object.stride != startup.stride ||
                object.vertex_bytes.size() != startup.vertex_bytes.size() ||
                object.attributes.size() != startup.attributes.size()) {
                throw std::runtime_error(
                    "Phase 648 object-space baseline does not match startup draw");
            }

            const auto& draw = runtime.material_draws.at(draw_index);
            LiveVehicleVertexBufferTarget target{};
            target.device = runtime.device;
            target.memory = draw.vertex_buffer.memory;
            target.vertex_payload_bytes = object.vertex_bytes.size();
            wiring.object_geometries[draw_index] = std::move(object);
            wiring.targets[draw_index] = target;
        }

        std::cout
            << "{\"format\":\"" << kRuntimeVehicleVulkanWiringFormat
            << "\",\"ready\":true"
            << ",\"vehicle_draw_count\":" << wiring.vehicle_indices.size()
            << ",\"script_steps\":" << wiring.script.steps.size()
            << ",\"upload_primitive\":\""
            << kLiveVehicleVertexBufferUploadFormat << "\""
            << ",\"source\":\"phase646-script-regression\""
            << ",\"phase706_snapshot_abi_compatible\":true"
            << ",\"retail_producer_claimed\":false}\n";
    }

    if (!wiring.enabled) {
        return;
    }
    if (simulation_step >= wiring.script.steps.size()) {
        throw std::runtime_error(
            "Phase 648 simulation step exceeds transform script");
    }

    phase648_detail::wait_for_all_in_flight_frames(runtime);
    const auto result = upload_live_vehicle_vertex_buffers(
        wiring.groups,
        wiring.object_geometries,
        wiring.targets,
        wiring.script.steps[static_cast<std::size_t>(simulation_step)]);
    if (result.vehicle_draw_indices != wiring.vehicle_indices) {
        throw std::runtime_error(
            "Phase 648 runtime upload vehicle selection drifted from scene groups");
    }

    std::cout
        << "{\"format\":\"" << kRuntimeVehicleVulkanUploadFormat
        << "\",\"step\":" << simulation_step
        << ",\"vehicle_draw_count\":" << result.vehicle_draw_indices.size()
        << ",\"uploaded_bytes\":" << result.uploaded_bytes
        << ",\"track_draw_writes\":0"
        << ",\"all_frame_fences_waited\":true"
        << ",\"object_space_reapply\":true"
        << ",\"upload_primitive\":\""
        << kLiveVehicleVertexBufferUploadFormat << "\"}\n";
    ++wiring.upload_steps;
}

}  // namespace shift::runtime::render

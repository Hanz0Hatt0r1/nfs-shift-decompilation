#pragma once

#include "shift_persistent_vehicle_vulkan_upload.hpp"
#include "shift_phase648_runtime_vehicle_vulkan_wiring.hpp"

#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace shift::runtime::render {

inline constexpr const char* kPersistentVehicleRuntimeWiringFormat =
    "SHIFT.PersistentVehicleRuntimeWiring/1";

namespace phase715_detail {

struct PersistentVehicleRuntimeWiringState {
    bool persistent_state_published = false;
    bool attachment_ready = false;
    std::uint64_t publish_count = 0u;
    std::uint64_t upload_count = 0u;
    std::uint64_t last_published_commit_generation = 0u;
    std::uint64_t last_uploaded_commit_generation = 0u;
    std::uint64_t last_uploaded_simulation_step = 0u;
    shift::runtime::physics::PersistentBmwVehicleWorldTransformState
        published_state{};
    std::string scene_set{};
    std::vector<std::string> groups{};
    std::vector<VehicleObjectGeometry> object_geometries{};
    std::vector<LiveVehicleVertexBufferTarget> targets{};
    std::vector<std::size_t> vehicle_indices{};
};

inline PersistentVehicleRuntimeWiringState& state() {
    static PersistentVehicleRuntimeWiringState value{};
    return value;
}

template <typename RuntimeT, typename GeometryVector>
inline void initialize_attachment(
    RuntimeT& runtime,
    const GeometryVector& startup_geometry,
    const std::string& scene_set,
    bool scene_set_mode) {
    auto& wiring = state();
    if (wiring.attachment_ready) {
        if (wiring.scene_set != scene_set) {
            throw std::logic_error(
                "Phase 715 scene set changed after persistent renderer attachment");
        }
        return;
    }
    if (!scene_set_mode || scene_set.empty()) {
        throw std::runtime_error(
            "Phase 715 persistent vehicle runtime wiring requires --scene-set");
    }
    if (runtime.device == VK_NULL_HANDLE) {
        throw std::runtime_error(
            "Phase 715 persistent vehicle runtime wiring requires a Vulkan device");
    }
    if (startup_geometry.size() != runtime.material_draws.size()) {
        throw std::runtime_error(
            "Phase 715 startup geometry/Vulkan draw count mismatch");
    }

    const std::filesystem::path root(scene_set);
    wiring.groups = load_native_scene_draw_groups(
        (root / "bundle_set.groups").string(), startup_geometry.size());
    wiring.vehicle_indices = vehicle_draw_indices(wiring.groups);
    const auto paths = phase648_detail::load_scene_paths(
        root, startup_geometry.size());

    wiring.object_geometries.resize(startup_geometry.size());
    wiring.targets.resize(startup_geometry.size());
    for (const std::size_t draw_index : wiring.vehicle_indices) {
        auto object = phase648_detail::load_object_geometry(paths.at(draw_index));
        const auto& startup = startup_geometry.at(draw_index);
        if (object.stride != startup.stride ||
            object.vertex_bytes.size() != startup.vertex_bytes.size() ||
            object.attributes.size() != startup.attributes.size()) {
            throw std::runtime_error(
                "Phase 715 object-space baseline does not match startup draw");
        }

        const auto& draw = runtime.material_draws.at(draw_index);
        LiveVehicleVertexBufferTarget target{};
        target.device = runtime.device;
        target.memory = draw.vertex_buffer.memory;
        target.vertex_payload_bytes = object.vertex_bytes.size();
        wiring.object_geometries[draw_index] = std::move(object);
        wiring.targets[draw_index] = target;
    }

    wiring.scene_set = scene_set;
    wiring.attachment_ready = true;

    std::cout
        << "{\"format\":\"" << kPersistentVehicleRuntimeWiringFormat
        << "\",\"phase\":715,\"ready\":true"
        << ",\"vehicle_draw_count\":" << wiring.vehicle_indices.size()
        << ",\"source\":\"phase706-persistent-state\""
        << ",\"test_motion_script_used\":false"
        << ",\"renderer_transform_producer_claimed\":false}\n";
}

}  // namespace phase715_detail

// Process 2 publishes only an already-committed Phase 706 state. This function
// does not commit a matrix, select a BODY, schedule physics, or manufacture a
// transform. Commit generations must advance monotonically after publication.
inline void publish_persistent_bmw_vehicle_world_transform_for_render(
    const shift::runtime::physics::PersistentBmwVehicleWorldTransformState&
        state) {
    if (!state.ready || state.commit_generation == 0u) {
        throw std::invalid_argument(
            "Phase 715 requires a ready committed Phase 706 vehicle transform");
    }

    auto& wiring = phase715_detail::state();
    if (wiring.persistent_state_published &&
        state.commit_generation <= wiring.last_published_commit_generation) {
        throw std::logic_error(
            "Phase 715 persistent transform publication did not advance generation");
    }

    wiring.published_state = state;
    wiring.last_published_commit_generation = state.commit_generation;
    wiring.persistent_state_published = true;
    ++wiring.publish_count;
}

// Production-facing renderer sink. Until Process 2 publishes a positive Phase
// 706 state this hook is intentionally inert, preserving the established
// Silverstone + BMW render path. Once publication starts, every admitted hook
// invocation requires a new commit generation and delegates freshness checking
// and GPU synchronization to Phase 649 before any vertex memory mutation.
template <typename RuntimeT, typename GeometryVector>
inline void phase715_after_fixed_step(
    RuntimeT& runtime,
    const GeometryVector& startup_geometry,
    const std::string& scene_set,
    bool scene_set_mode,
    const shift::runtime::NativeRuntimeState& native_state,
    std::uint64_t simulation_step) {
    auto& wiring = phase715_detail::state();
    if (!wiring.persistent_state_published) {
        return;
    }

    const char* script_path =
        std::getenv(kRuntimeVehicleWorldTransformScriptEnv);
    if (script_path != nullptr && *script_path != '\0') {
        throw std::logic_error(
            "Phase 715 persistent transform and Phase 648 test-motion script cannot both drive vehicle rendering");
    }

    phase715_detail::initialize_attachment(
        runtime, startup_geometry, scene_set, scene_set_mode);

    if (wiring.last_uploaded_commit_generation != 0u &&
        wiring.published_state.commit_generation <=
            wiring.last_uploaded_commit_generation) {
        throw std::logic_error(
            "Phase 715 current vehicle transform was not refreshed for this runtime step");
    }

    const auto result = upload_current_bmw_vehicle_world_transform_to_vulkan(
        runtime.device,
        runtime.fences.data(),
        runtime.fences.size(),
        wiring.groups,
        wiring.object_geometries,
        wiring.targets,
        wiring.published_state,
        native_state);
    if (result.upload.vehicle_draw_indices != wiring.vehicle_indices) {
        throw std::runtime_error(
            "Phase 715 runtime upload vehicle selection drifted from authoritative scene groups");
    }
    if (result.snapshot.commit_generation !=
        wiring.published_state.commit_generation) {
        throw std::runtime_error(
            "Phase 715 lost the published Phase 706 commit generation");
    }

    wiring.last_uploaded_commit_generation = result.snapshot.commit_generation;
    wiring.last_uploaded_simulation_step = simulation_step;
    ++wiring.upload_count;

    std::cout
        << "{\"format\":\"" << kPersistentVehicleRuntimeWiringFormat
        << "\",\"phase\":715"
        << ",\"step\":" << simulation_step
        << ",\"commit_generation\":" << result.snapshot.commit_generation
        << ",\"vehicle_draw_count\":"
        << result.upload.vehicle_draw_indices.size()
        << ",\"uploaded_bytes\":" << result.upload.uploaded_bytes
        << ",\"all_frame_fences_waited\":"
        << (result.all_frame_fences_waited ? "true" : "false")
        << ",\"test_motion_script_used\":false"
        << ",\"renderer_transform_producer_claimed\":false}\n";
}

}  // namespace shift::runtime::render

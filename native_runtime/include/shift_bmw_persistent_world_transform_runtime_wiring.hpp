#pragma once

#include "shift_bmw_body0_bind_frame_runtime_admission.hpp"
#include "shift_phase648_runtime_vehicle_vulkan_wiring.hpp"
#include "shift_phase715_persistent_vehicle_runtime_wiring.hpp"
#include "shift_retail_global_vehicle_body_owner_identity.hpp"
#include "shift_vehicle_world_transform_transport.hpp"

#include <array>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kBmwPersistentWorldTransformRuntimeWiringFormat =
    "SHIFT.BMWPersistentWorldTransformRuntimeWiring/1";

namespace bmw_persistent_world_transform_runtime_detail {

#pragma pack(push, 1)
struct SvwtHeader {
    char magic[4];
    std::uint32_t version;
    std::uint32_t convention;
    std::uint32_t matrix_bytes;
};
#pragma pack(pop)

static_assert(sizeof(SvwtHeader) == 16u);

struct WiringState {
    bool static_vhf_bind_ready = false;
    std::string scene_set{};
    std::size_t draw_count = 0u;
    std::vector<std::size_t> vehicle_draw_indices{};
    ProvenBmwVhfBindFrame vhf_bind{};
    PersistentBmwVehicleWorldTransformState persistent{};
    std::uint64_t commit_count = 0u;
};

inline WiringState& state() {
    static WiringState value{};
    return value;
}

inline shift::runtime::render::VehicleWorldMatrix load_svwt_matrix(
    const std::filesystem::path& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) {
        throw std::runtime_error(
            "S4 cannot open authoritative vehicle world_transform.svwt: " +
            path.string());
    }
    const std::streamsize size = file.tellg();
    constexpr std::size_t kExpectedBytes =
        sizeof(SvwtHeader) + 16u * sizeof(float);
    if (size != static_cast<std::streamsize>(kExpectedBytes)) {
        throw std::runtime_error(
            "S4 authoritative vehicle SVWT packet size mismatch");
    }
    file.seekg(0);

    SvwtHeader header{};
    if (!file.read(reinterpret_cast<char*>(&header), sizeof(header))) {
        throw std::runtime_error(
            "S4 authoritative vehicle SVWT header is truncated");
    }
    if (std::memcmp(header.magic, "SVWT", 4u) != 0 ||
        header.version != 1u || header.convention != 1u ||
        header.matrix_bytes != 16u * sizeof(float)) {
        throw std::runtime_error(
            "S4 authoritative vehicle SVWT packet ABI mismatch");
    }

    shift::runtime::render::VehicleWorldMatrix matrix{};
    if (!file.read(
            reinterpret_cast<char*>(matrix.data()),
            static_cast<std::streamsize>(matrix.size() * sizeof(float)))) {
        throw std::runtime_error(
            "S4 authoritative vehicle SVWT matrix is truncated");
    }
    shift::runtime::render::validate_vehicle_world_matrix(matrix);
    return matrix;
}

inline bool exact_same_matrix(
    const shift::runtime::render::VehicleWorldMatrix& lhs,
    const shift::runtime::render::VehicleWorldMatrix& rhs) {
    return std::memcmp(
               lhs.data(), rhs.data(), lhs.size() * sizeof(float)) == 0;
}

inline ProvenBmwVhfBindFrame resolve_authoritative_vehicle_vhf_bind(
    const std::string& scene_set,
    std::size_t expected_draw_count,
    std::vector<std::size_t>* selected_indices = nullptr) {
    if (scene_set.empty()) {
        throw std::runtime_error(
            "S4 persistent BMW world transform requires --scene-set");
    }
    if (expected_draw_count == 0u) {
        throw std::runtime_error(
            "S4 persistent BMW world transform requires non-empty scene draws");
    }

    const std::filesystem::path root(scene_set);
    const auto groups = shift::runtime::render::load_native_scene_draw_groups(
        (root / "bundle_set.groups").string(), expected_draw_count);
    const auto vehicle_indices =
        shift::runtime::render::vehicle_draw_indices(groups);
    const auto paths = shift::runtime::render::phase648_detail::load_scene_paths(
        root, expected_draw_count);

    bool have_matrix = false;
    shift::runtime::render::VehicleWorldMatrix authoritative{};
    for (const std::size_t draw_index : vehicle_indices) {
        if (draw_index >= paths.size()) {
            throw std::runtime_error(
                "S4 vehicle draw index exceeds scene path table");
        }
        const auto candidate = load_svwt_matrix(
            paths[draw_index] / "world_transform.svwt");
        if (!have_matrix) {
            authoritative = candidate;
            have_matrix = true;
        } else if (!exact_same_matrix(authoritative, candidate)) {
            throw std::runtime_error(
                "S4 vehicle draws disagree on canonical BMW VHF bind matrix");
        }
    }
    if (!have_matrix) {
        throw std::runtime_error(
            "S4 scene has no authoritative vehicle VHF bind matrix");
    }

    if (selected_indices != nullptr) {
        *selected_indices = vehicle_indices;
    }
    ProvenBmwVhfBindFrame result{};
    result.proven = true;
    result.body_meb_to_vhf_vehicle_root = authoritative;
    return result;
}

inline void ensure_static_vhf_bind(
    WiringState& wiring,
    const std::string& scene_set,
    std::size_t expected_draw_count) {
    if (wiring.static_vhf_bind_ready) {
        if (wiring.scene_set != scene_set ||
            wiring.draw_count != expected_draw_count) {
            throw std::logic_error(
                "S4 scene-set identity changed after BMW VHF bind admission");
        }
        return;
    }

    wiring.vhf_bind = resolve_authoritative_vehicle_vhf_bind(
        scene_set, expected_draw_count, &wiring.vehicle_draw_indices);
    wiring.scene_set = scene_set;
    wiring.draw_count = expected_draw_count;
    wiring.static_vhf_bind_ready = true;
}

}  // namespace bmw_persistent_world_transform_runtime_detail

// Production-facing S4 continuation.  The positive BBFP packet is admitted
// before fixed_step() by the existing Phase 704 hook.  This function must run
// after fixed_step(), when NativeRuntimeState contains the current BODY0 pose,
// and before Phase 715 consumes the newly published persistent transform.
//
// Absence of a positive BBFP admission remains inert.  Once admission is
// positive, scene/VHF-bind ambiguity or stale BODY provenance fails closed.
inline bool commit_and_publish_admitted_bmw_world_transform_after_fixed_step(
    const shift::runtime::NativeRuntimeState& runtime,
    const std::string& scene_set,
    bool scene_set_mode,
    std::size_t expected_draw_count) {
    const auto& admission =
        current_bmw_body0_bind_frame_runtime_admission();
    if (!admission.admitted) {
        return false;
    }
    if (!admission.configured ||
        !admission.bind_frame.ready ||
        !admission.bind_frame.evidence_proven_static) {
        throw std::logic_error(
            "S4 observed non-positive BODY0 bind runtime admission");
    }
    if (!scene_set_mode) {
        throw std::runtime_error(
            "S4 admitted BMW world transform requires native --scene-set mode");
    }

    auto& wiring =
        bmw_persistent_world_transform_runtime_detail::state();
    bmw_persistent_world_transform_runtime_detail::ensure_static_vhf_bind(
        wiring, scene_set, expected_draw_count);

    const auto snapshot = commit_retail_bmw_vehicle_world_transform(
        wiring.persistent,
        runtime,
        wiring.vhf_bind,
        admission.bind_frame);
    if (!wiring.persistent.ready || snapshot.commit_generation == 0u ||
        snapshot.commit_generation != wiring.persistent.commit_generation) {
        throw std::logic_error(
            "S4 persistent BMW world-transform commit failed");
    }

    shift::runtime::render::publish_persistent_bmw_vehicle_world_transform_for_render(
        wiring.persistent);
    ++wiring.commit_count;

    std::cout
        << "{\"format\":\""
        << kBmwPersistentWorldTransformRuntimeWiringFormat
        << "\",\"ready\":true"
        << ",\"body_index\":" << wiring.persistent.body_index
        << ",\"commit_generation\":"
        << wiring.persistent.commit_generation
        << ",\"source_pose_snapshot_generation\":"
        << wiring.persistent.source_pose_snapshot_generation
        << ",\"source_explicit_update_count\":"
        << wiring.persistent.source_explicit_update_count
        << ",\"vehicle_draw_count\":"
        << wiring.vehicle_draw_indices.size()
        << ",\"bind_proof_admitted\":true"
        << ",\"persistent_world_transform_published\":true"
        << ",\"retail_scheduler_claimed\":false"
        << ",\"test_motion_script_used\":false}\n";
    return true;
}

inline const PersistentBmwVehicleWorldTransformState&
current_admitted_bmw_persistent_world_transform() {
    return bmw_persistent_world_transform_runtime_detail::state().persistent;
}

}  // namespace shift::runtime::physics

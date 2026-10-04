#pragma once

#include "shift_vehicle_body_pose_selection.hpp"
#include "shift_vehicle_world_transform_transport.hpp"

#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBmwBody0VhfWorldMatrixCompositionFormat =
    "SHIFT.NativeBMWBody0VHFWorldMatrixComposition/1";

struct ProvenBmwVhfBindFrame {
    bool proven = false;
    shift::runtime::render::VehicleWorldMatrix
        body_meb_to_vhf_vehicle_root{};
};

struct ProvenBmwBody0BindFrame {
    bool ready = false;
    bool evidence_proven_static = false;
    std::uint32_t body_index = 0u;
    bool identity_matrix_assumed = false;
    shift::runtime::render::VehicleWorldMatrix
        body0_local_to_vhf_vehicle_root{};
};

struct BmwBody0VhfWorldMatrixCompositionResult {
    shift::runtime::render::VehicleWorldMatrix body0_runtime_row{};
    shift::runtime::render::VehicleWorldMatrix vehicle_world_matrix{};
};

BmwBody0VhfWorldMatrixCompositionResult
compose_bmw_body0_pose_to_vehicle_world_matrix(
    const SelectedVehicleBodyPose& body0_pose,
    const ProvenBmwVhfBindFrame& vhf_bind,
    const ProvenBmwBody0BindFrame& body0_bind);

}  // namespace shift::runtime::physics

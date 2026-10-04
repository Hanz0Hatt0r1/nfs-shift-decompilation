#pragma once

#include "shift_bmw_body0_vhf_world_matrix_composition.hpp"
#include "shift_global_vehicle_body_owner_selection.hpp"

#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBmwVehicleWorldMatrixRuntimeHandoffFormat =
    "SHIFT.NativeBMWVehicleWorldMatrixRuntimeHandoff/1";

struct BmwVehicleWorldMatrixRuntimeHandoffResult {
    SelectedVehicleBodyPose pose{};
    shift::runtime::render::VehicleWorldMatrix body0_runtime_row{};
    shift::runtime::render::VehicleWorldMatrix vehicle_world_matrix{};
    std::uint32_t runtime_body_count = 0u;
    std::uint64_t explicit_update_count = 0u;
};

BmwVehicleWorldMatrixRuntimeHandoffResult
build_bmw_vehicle_world_matrix_runtime_handoff(
    const shift::runtime::NativeRuntimeState& runtime,
    const GlobalVehicleBodyOwnerIdentityHandoff& identity,
    const ProvenBmwVhfBindFrame& vhf_bind,
    const ProvenBmwBody0BindFrame& body0_bind);

}  // namespace shift::runtime::physics

#pragma once

#include "runtime_state.hpp"
#include "shift_vehicle_body_pose_selection.hpp"

#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kNativeVehicleBodyPoseRuntimeHandoffFormat =
    "SHIFT.NativeVehicleBodyPoseRuntimeHandoff/1";

struct VehicleBodyPoseRuntimeHandoffResult {
    SelectedVehicleBodyPose pose{};
    std::uint32_t runtime_body_count = 0u;
    std::uint64_t explicit_update_count = 0u;
};

VehicleBodyPoseRuntimeHandoffResult build_vehicle_body_pose_runtime_handoff(
    const shift::runtime::NativeRuntimeState& runtime,
    const VehicleBodyIdentitySelection& selection);

}  // namespace shift::runtime::physics

#pragma once

#include "shift_vehicle_body_pose_runtime_handoff.hpp"

#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kNativeGlobalVehicleBodyOwnerSelectionFormat =
    "SHIFT.NativeGlobalVehicleBodyOwnerSelection/1";

struct GlobalVehicleBodyOwnerIdentityHandoff {
    bool outer_receiver_to_body_owner_continuity_proven = false;
    bool vehicle_body_selection_ready = false;
    bool selected_body_index_present = false;
    std::uint32_t selected_body_index = 0u;
    bool phase698_positive_selection_admissible = false;
    bool phase700_runtime_handoff_admissible = false;
    bool phase703_update_child_equality_gate_required = false;
    bool phase703_gate_rewrite_ready = false;
};

VehicleBodyIdentitySelection
build_vehicle_body_identity_selection_from_global_owner(
    const GlobalVehicleBodyOwnerIdentityHandoff& handoff);

VehicleBodyPoseRuntimeHandoffResult
build_global_vehicle_body_pose_runtime_handoff(
    const shift::runtime::NativeRuntimeState& runtime,
    const GlobalVehicleBodyOwnerIdentityHandoff& handoff);

}  // namespace shift::runtime::physics

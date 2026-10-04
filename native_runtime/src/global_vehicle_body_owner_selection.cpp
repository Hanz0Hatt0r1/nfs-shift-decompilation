#include "shift_global_vehicle_body_owner_selection.hpp"

#include <stdexcept>

namespace shift::runtime::physics {
namespace {

constexpr std::uint32_t kRetailBmwChassisBodyIndex = 0u;

void validate_global_owner_handoff(
    const GlobalVehicleBodyOwnerIdentityHandoff& handoff) {
    if (handoff.phase703_update_child_equality_gate_required) {
        throw std::invalid_argument(
            "global vehicle BODY-owner identity reintroduced obsolete update-child equality gate");
    }
    const bool ready = handoff.outer_receiver_to_body_owner_continuity_proven;
    if (handoff.vehicle_body_selection_ready != ready ||
        handoff.phase698_positive_selection_admissible != ready ||
        handoff.phase700_runtime_handoff_admissible != ready ||
        handoff.phase703_gate_rewrite_ready != ready) {
        throw std::invalid_argument(
            "global vehicle BODY-owner identity readiness flags disagree");
    }
    if (!ready) {
        if (handoff.selected_body_index_present) {
            throw std::invalid_argument(
                "blocked global vehicle BODY-owner identity preclaims a BODY index");
        }
        throw std::invalid_argument(
            "global vehicle BODY-owner identity is not retail-ready");
    }
    if (!handoff.selected_body_index_present ||
        handoff.selected_body_index != kRetailBmwChassisBodyIndex) {
        throw std::invalid_argument(
            "positive global vehicle BODY-owner identity must select retail BMW chassis BODY 0");
    }
}

}  // namespace

VehicleBodyIdentitySelection
build_vehicle_body_identity_selection_from_global_owner(
    const GlobalVehicleBodyOwnerIdentityHandoff& handoff) {
    validate_global_owner_handoff(handoff);
    return VehicleBodyIdentitySelection{true, handoff.selected_body_index};
}

VehicleBodyPoseRuntimeHandoffResult
build_global_vehicle_body_pose_runtime_handoff(
    const shift::runtime::NativeRuntimeState& runtime,
    const GlobalVehicleBodyOwnerIdentityHandoff& handoff) {
    const auto selection =
        build_vehicle_body_identity_selection_from_global_owner(handoff);
    return build_vehicle_body_pose_runtime_handoff(runtime, selection);
}

}  // namespace shift::runtime::physics

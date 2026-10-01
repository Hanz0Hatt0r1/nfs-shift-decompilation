#pragma once

#include "shift_constraint_relation_reset_frame.hpp"
#include "shift_constraint_sample_relation_frame.hpp"

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

struct ConstraintRelationStateMutationResult {
    PreparedConstraintRelationResetFrame frame;
    std::size_t matched_joint_relation_count = 0;
    std::size_t matched_hinge_relation_count = 0;
    std::size_t matched_bar_relation_count = 0;
    std::size_t newly_set_joint_relation_count = 0;
    std::size_t newly_set_hinge_relation_count = 0;
    std::size_t newly_set_bar_relation_count = 0;
};

inline constexpr std::size_t kVehicleConstraintComponentCount = 4u;
inline constexpr std::size_t kVehicleConstraintComponentBaseOffset = 0x400u;
inline constexpr std::size_t kVehicleConstraintComponentStride = 0xA80u;
inline constexpr std::size_t kVehicleConstraintWheelBodyFieldOffset = 0x420u;
inline constexpr std::size_t kVehicleConstraintSpindleBodyFieldOffset = 0x424u;
inline constexpr std::size_t kVehicleConstraintRearAxleBodyFieldOffset = 0x2E00u;
inline constexpr std::size_t kVehicleConstraintSetupConfigComponentBaseOffset = 0x88u;
inline constexpr std::size_t kVehicleConstraintSetupConfigComponentStride = 0xA0u;
inline constexpr std::size_t kVehicleConstraintSetupMutationFlagOffset = 0x98u;

inline constexpr std::size_t
vehicle_constraint_setup_mutation_flag_source_offset(
    std::size_t component_slot) {
    return
        kVehicleConstraintSetupConfigComponentBaseOffset +
        component_slot * kVehicleConstraintSetupConfigComponentStride +
        kVehicleConstraintSetupMutationFlagOffset;
}

struct VehicleConstraintBodyIdentityMap {
    std::array<std::size_t, kVehicleConstraintComponentCount>
        wheel_body_indices{};
    std::array<std::size_t, kVehicleConstraintComponentCount>
        spindle_body_indices{};
    std::size_t rear_axle_body_index = 0;
};

struct ConstraintRelationStateDispatchResult {
    ConstraintRelationStateMutationResult mutation;
    std::size_t component_slot = 0;
    std::size_t component_block_offset = 0;
    std::size_t wheel_body_index = 0;
    std::size_t spindle_body_index = 0;
    std::size_t rear_axle_body_index = 0;
    bool spindle_body_present = false;
};

struct VehicleConstraintRelationInitializationState {
    std::array<bool, kVehicleConstraintComponentCount>
        mutation_enabled{};
    std::array<bool, kVehicleConstraintComponentCount>
        spindle_body_present{};
};

struct ConstraintRelationStateInitializationResult {
    PreparedConstraintRelationResetFrame frame;
    std::array<bool, kVehicleConstraintComponentCount>
        slot_dispatched{};
    std::array<std::size_t, kVehicleConstraintComponentCount>
        dispatched_slot_order{};
    std::size_t dispatched_slot_count = 0;
    std::size_t pair_branch_dispatch_count = 0;
    std::size_t bar_branch_dispatch_count = 0;
    std::size_t matched_joint_relation_count = 0;
    std::size_t matched_hinge_relation_count = 0;
    std::size_t matched_bar_relation_count = 0;
    std::size_t newly_set_joint_relation_count = 0;
    std::size_t newly_set_hinge_relation_count = 0;
    std::size_t newly_set_bar_relation_count = 0;
};

ConstraintRelationStateDispatchResult
dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    const VehicleConstraintBodyIdentityMap& body_map,
    std::size_t component_slot,
    bool spindle_body_present);

ConstraintRelationStateInitializationResult
apply_fun_0076ed60_vehicle_relation_state_initialization(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    const VehicleConstraintBodyIdentityMap& body_map,
    const VehicleConstraintRelationInitializationState& initialization);

ConstraintRelationStateMutationResult
apply_fun_00757d2c_pair_relation_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    std::size_t first_body_index,
    std::size_t second_body_index);

ConstraintRelationStateMutationResult
apply_fun_00757d2c_bar_endpoint_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    std::size_t body_index);

}  // namespace shift::runtime::physics

#pragma once

#include "shift_constraint_relation_reset_frame.hpp"
#include "shift_constraint_sample_relation_frame.hpp"

#include <array>
#include <cstddef>
#include <optional>

namespace shift::runtime::physics {

enum class ConstraintRelationStateMutationBranch {
    JointHingePair,
    BarEndpoint,
};

struct ConstraintRelationStateMutationResult {
    PreparedConstraintRelationResetFrame frame;
    std::size_t matched_joint_relation_count = 0;
    std::size_t matched_hinge_relation_count = 0;
    std::size_t matched_bar_relation_count = 0;
    std::size_t newly_set_joint_relation_count = 0;
    std::size_t newly_set_hinge_relation_count = 0;
    std::size_t newly_set_bar_relation_count = 0;
    ConstraintRelationStateMutationBranch branch =
        ConstraintRelationStateMutationBranch::JointHingePair;
    bool component_state_504_set = false;
    bool component_state_540_set = false;
};

struct ConstraintRelationComponentIdentity {
    std::optional<std::size_t> primary_body_index;
    std::optional<std::size_t> secondary_body_index;
};

struct ConstraintRelationVehicleComponentMap {
    std::array<ConstraintRelationComponentIdentity, 4> components{};
    std::optional<std::size_t> rear_axle_body_index;
};

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

ConstraintRelationStateMutationResult
apply_fun_00757d2c_component_relation_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    std::optional<std::size_t> primary_body_index,
    std::optional<std::size_t> secondary_body_index,
    std::optional<std::size_t> rear_axle_body_index);

ConstraintRelationStateMutationResult
apply_fun_00757d20_component_slot_relation_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    const ConstraintRelationVehicleComponentMap& component_map,
    std::size_t component_slot);

}  // namespace shift::runtime::physics

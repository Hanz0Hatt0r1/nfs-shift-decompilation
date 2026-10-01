#pragma once

#include "shift_constraint_relation_reset_frame.hpp"
#include "shift_constraint_sample_relation_frame.hpp"

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

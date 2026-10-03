#pragma once

#include "shift_builtin_solver_frame.hpp"
#include "shift_constraint_relation_reset_frame.hpp"
#include "shift_constraint_sample_relation_frame.hpp"
#include "shift_generated_body_constraint_frame.hpp"
#include "shift_post_solve_projection.hpp"

#include <cstddef>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBodyStateFeedbackContractFormat =
    "SHIFT.NativeBodyStateFeedbackContract/1";
inline constexpr const char* kNativeBodyStateFeedbackStepFormat =
    "SHIFT.NativeBodyStateFeedbackStep/1";

struct BodyStateFeedbackContractResult {
    std::size_t body_count = 0;
    std::size_t joint_relation_count = 0;
    std::size_t hinge_relation_count = 0;
    std::size_t bar_relation_count = 0;
    double max_seed_error = 0.0;
    double max_row_error = 0.0;
};

struct BodyStateFeedbackStepResult {
    std::vector<double> generated_rhs;
    std::vector<double> solved_vector;
    std::vector<BodyAccumulatorState> bodies;
    std::size_t reset_call_count = 0;
    std::size_t reset_node_count = 0;
    double max_matrix_anchor_error = 0.0;
};

BodyStateFeedbackContractResult verify_body_state_feedback_contract(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedPostSolveBodyProjection& projection,
    double tolerance = 1e-10);

PreparedGeneratedBodyConstraintFrame apply_body_accumulator_feedback(
    const PreparedGeneratedBodyConstraintFrame& source,
    const std::vector<BodyAccumulatorState>& bodies);

BodyStateFeedbackStepResult execute_body_state_feedback_step(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<BodyAccumulatorState>& current_bodies,
    double tolerance = 1e-10);

}  // namespace shift::runtime::physics

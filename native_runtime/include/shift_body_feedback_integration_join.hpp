#pragma once

#include "shift_body_feedback_record_bridge.hpp"
#include "shift_body_record_adapter.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBodyFeedbackIntegrationJoinFormat =
    "SHIFT.NativeBodyFeedbackIntegrationJoin/1";
inline constexpr const char* kHalfStepAnchorFunction = "FUN_00765470";
inline constexpr const char* kPostSolveFeedbackFunction = "FUN_007b4110";

struct BodyFeedbackIntegrationJoinResult {
    std::vector<std::uint8_t> body_bytes;
    std::vector<double> generated_rhs;
    std::vector<double> solved_vector;
    std::size_t reset_call_count = 0;
    std::size_t reset_node_count = 0;
    double max_matrix_anchor_error = 0.0;
};

BodyFeedbackIntegrationJoinResult execute_proven_body_feedback_integration_join(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<std::uint8_t>& body_bytes,
    double timestep,
    const BodyBasisRotationCallback& basis_rotation,
    double tolerance = 1e-10);

}  // namespace shift::runtime::physics

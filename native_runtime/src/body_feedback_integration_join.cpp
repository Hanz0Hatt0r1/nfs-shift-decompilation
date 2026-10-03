#include "shift_body_feedback_integration_join.hpp"

#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {

BodyFeedbackIntegrationJoinResult execute_proven_body_feedback_integration_join(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<std::uint8_t>& body_bytes,
    double timestep,
    const BodyBasisRotationCallback& basis_rotation,
    double tolerance) {

    if (!std::isfinite(timestep)) {
        throw std::invalid_argument(
            "BODY feedback/integration join timestep must be finite");
    }
    if (!basis_rotation) {
        throw std::invalid_argument(
            "BODY feedback/integration join requires basis rotation provider");
    }

    // Static schedule evidence places post-solve BODY feedback before the BODY
    // array integration anchor inside FUN_00765470.  Preserve that exact anchor
    // order without claiming the omitted surrounding helper work is implemented.
    const auto feedback = execute_body_state_feedback_raw_step(
        source,
        relations,
        reset_state,
        solver_topology,
        projection,
        body_bytes,
        tolerance);

    const auto integrated = execute_fun_007b2270_body_buffer_with_basis_callback(
        feedback.body_bytes,
        source.bodies.size(),
        timestep,
        basis_rotation);

    return {
        integrated,
        feedback.generated_rhs,
        feedback.solved_vector,
        feedback.reset_call_count,
        feedback.reset_node_count,
        feedback.max_matrix_anchor_error,
    };
}

}  // namespace shift::runtime::physics

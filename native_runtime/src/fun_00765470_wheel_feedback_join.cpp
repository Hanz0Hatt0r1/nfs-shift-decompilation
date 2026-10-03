#include "shift_fun_00765470_wheel_feedback_join.hpp"

#include <stdexcept>

namespace shift::runtime::physics {

Fun00765470WheelFeedbackJoinResult execute_fun_00765470_wheel_feedback_join(
    const Fun00763570WheelSharedTripletCallback& wheel_shared_triplet,
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<std::uint8_t>& body_bytes,
    double timestep,
    const BodyBasisRotationCallback& basis_rotation,
    double tolerance) {
    if (!wheel_shared_triplet) {
        throw std::invalid_argument(
            "FUN_00765470 proven join requires FUN_00763570 callback");
    }

    Fun00765470WheelFeedbackJoinResult result{};
    wheel_shared_triplet();
    result.wheel_shared_triplet_anchor_count = 1u;

    result.feedback_integration = execute_proven_body_feedback_integration_join(
        source,
        relations,
        reset_state,
        solver_topology,
        projection,
        body_bytes,
        timestep,
        basis_rotation,
        tolerance);
    return result;
}

}  // namespace shift::runtime::physics

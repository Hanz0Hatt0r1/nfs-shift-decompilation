#pragma once

#include "shift_body_feedback_integration_join.hpp"

#include <cstddef>
#include <functional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun00765470WheelFeedbackJoinFormat =
    "SHIFT.NativeFun00765470WheelFeedbackJoin/1";
inline constexpr const char* kFun00765470HalfStepFunction = "FUN_00765470";
inline constexpr const char* kFun00763570WheelSharedTripletFunction = "FUN_00763570";

using Fun00763570WheelSharedTripletCallback = std::function<void()>;

struct Fun00765470WheelFeedbackJoinResult {
    BodyFeedbackIntegrationJoinResult feedback_integration{};
    std::size_t wheel_shared_triplet_anchor_count = 0u;
};

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
    double tolerance = 1e-10);

}  // namespace shift::runtime::physics

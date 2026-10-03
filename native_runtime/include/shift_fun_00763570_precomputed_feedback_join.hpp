#pragma once

#include "shift_fun_00765470_wheel_feedback_join.hpp"
#include "shift_wheel_longitudinal_velocity.hpp"

#include <array>
#include <cstddef>
#include <functional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun00763570PrecomputedFeedbackJoinFormat =
    "SHIFT.NativeFun00763570PrecomputedFeedbackJoin/1";

struct Fun00763570PrecomputedInput {
    std::array<WheelLongitudinalInput, kWheelLongitudinalCount> wheels{};
    bool rear_pair_average_enabled = false;
    int mode = 0;
    bool global_config_byte = false;
};

using Fun00763570PrecomputedProvider =
    std::function<Fun00763570PrecomputedInput()>;

struct Fun00763570PrecomputedFeedbackJoinResult {
    WheelLongitudinalBatchResult longitudinal{};
    Fun00765470WheelFeedbackJoinResult half_step{};
    std::size_t provider_call_count = 0u;
};

Fun00763570PrecomputedFeedbackJoinResult
execute_fun_00765470_precomputed_longitudinal_feedback_join(
    const Fun00763570PrecomputedProvider& precomputed_provider,
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

#pragma once

#include "shift_constraint_sample_refresh.hpp"
#include "shift_fun_00763570_precomputed_feedback_join.hpp"

#include <array>
#include <cstddef>
#include <functional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun00763570MachineFeedbackJoinFormat =
    "SHIFT.NativeFun00763570MachineFeedbackJoin/1";

struct WheelLongitudinalMachineInput {
    std::size_t wheel_index = 0u;
    ConstraintRefreshFrame3f body_frame{};
    WheelLongitudinalVector3d shared_velocity{};
};

struct Fun00763570MachineInput {
    std::array<WheelLongitudinalMachineInput, kWheelLongitudinalCount> wheels{};
    bool rear_pair_average_enabled = false;
    int mode = 0;
    bool global_config_byte = false;
};

using Fun00763570MachineProvider =
    std::function<Fun00763570MachineInput()>;

struct Fun00763570MachineFeedbackJoinResult {
    Fun00763570PrecomputedFeedbackJoinResult joined{};
    std::size_t provider_call_count = 0u;
    std::size_t machine_transform_wheel_count = 0u;
};

Fun00763570PrecomputedInput build_fun_00763570_machine_precomputed_input(
    const Fun00763570MachineInput& input);

Fun00763570MachineFeedbackJoinResult
execute_fun_00765470_machine_longitudinal_feedback_join(
    const Fun00763570MachineProvider& machine_provider,
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

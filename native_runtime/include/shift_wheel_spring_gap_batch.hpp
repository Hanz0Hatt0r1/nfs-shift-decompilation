#pragma once

#include "shift_wheel_spring_gap_join.hpp"

#include <array>
#include <cstddef>
#include <optional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelSpringGapBatchFormat =
    "SHIFT.NativeWheelSpringGapBatch/1";
inline constexpr const char* kWheelSpringGapBatchFunction = "FUN_00758b50";

struct WheelSpringGapBatchSlotInput {
    WheelKinematicSlotInput kinematic{};
    int spring_type = 0;
    double lower_boundary = 0.0;
    double upper_boundary = 0.0;
    double current_gap_before = 0.0;
};

struct WheelSpringGapBatchResult {
    std::array<bool, kWheelKinematicsCount> processed{};
    std::array<std::optional<WheelKinematicObservation>, kWheelKinematicsCount>
        kinematics{};
    std::array<std::optional<WheelSpringGapJoinResult>, kWheelKinematicsCount>
        spring_results{};
    std::array<std::size_t, kWheelKinematicsCount> processed_order{};
    std::size_t processed_count = 0u;
};

WheelSpringGapBatchResult execute_fun_00758b50_spring_gap_batch(
    const std::array<WheelSpringGapBatchSlotInput, kWheelKinematicsCount>& inputs);

}  // namespace shift::runtime::physics

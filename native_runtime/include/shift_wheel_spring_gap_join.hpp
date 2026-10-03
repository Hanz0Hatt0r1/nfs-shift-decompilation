#pragma once

#include "shift_spring_gap_state.hpp"
#include "shift_wheel_kinematics.hpp"

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelSpringGapJoinFormat =
    "SHIFT.NativeWheelSpringGapJoin/1";

struct WheelSpringGapJoinInput {
    WheelKinematicObservation kinematic{};
    int spring_type = 0;
    double lower_boundary = 0.0;
    double upper_boundary = 0.0;
    double current_gap_before = 0.0;
};

struct WheelSpringGapJoinResult {
    std::size_t wheel_index = 0u;
    double displacement = 0.0;
    double trigger_value = 0.0;
    SpringGapStateResult spring_state{};
};

WheelSpringGapJoinResult execute_fun_00755950_spring_gap_join(
    const WheelSpringGapJoinInput& input);

}  // namespace shift::runtime::physics

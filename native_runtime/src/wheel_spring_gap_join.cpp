#include "shift_wheel_spring_gap_join.hpp"

#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {

WheelSpringGapJoinResult execute_fun_00755950_spring_gap_join(
    const WheelSpringGapJoinInput& input) {

    const auto& kinematic = input.kinematic;
    if (kinematic.wheel_index >= kWheelKinematicsCount) {
        throw std::invalid_argument(
            "FUN_00755950 join wheel index must be in [0, 3]");
    }

    const std::size_t expected_state_offset =
        kWheelKinematicsStateBase +
        kinematic.wheel_index * kWheelKinematicsStateStride;
    const std::size_t expected_runtime_offset =
        kWheelKinematicsRuntimeBase +
        kinematic.wheel_index * kWheelKinematicsRuntimeStride;
    if (kinematic.wheel_state_offset != expected_state_offset ||
        kinematic.wheel_runtime_offset != expected_runtime_offset) {
        throw std::invalid_argument(
            "FUN_00755950 join rejected mismatched wheel topology");
    }

    if (!std::isfinite(kinematic.reference_length) ||
        !std::isfinite(kinematic.relative_length) ||
        !std::isfinite(kinematic.distance_error) ||
        !std::isfinite(kinematic.projection_input) ||
        !std::isfinite(kinematic.stored_projection_value)) {
        throw std::invalid_argument(
            "FUN_00755950 join contains non-finite kinematic state");
    }

    const double expected_displacement =
        kinematic.reference_length - kinematic.relative_length;
    if (kinematic.distance_error != expected_displacement) {
        throw std::invalid_argument(
            "FUN_00755950 join rejected mismatched distance-error handoff");
    }
    if (kinematic.stored_projection_value != -kinematic.projection_input) {
        throw std::invalid_argument(
            "FUN_00755950 join rejected mismatched projection handoff");
    }

    SpringGapStateInput spring_input{};
    spring_input.spring_type = input.spring_type;
    spring_input.displacement = kinematic.distance_error;
    spring_input.lower_boundary = input.lower_boundary;
    spring_input.upper_boundary = input.upper_boundary;
    spring_input.current_gap_before = input.current_gap_before;
    spring_input.trigger_value = kinematic.stored_projection_value;

    WheelSpringGapJoinResult result{};
    result.wheel_index = kinematic.wheel_index;
    result.displacement = kinematic.distance_error;
    result.trigger_value = kinematic.stored_projection_value;
    result.spring_state = execute_fun_007555b0_gap_state(spring_input);
    return result;
}

}  // namespace shift::runtime::physics

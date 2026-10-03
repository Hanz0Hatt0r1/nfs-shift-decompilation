#include "shift_wheel_kinematics.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

void require_finite_value(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string(label) + " must be finite");
    }
}

}  // namespace

WheelKinematicObservation prepare_fun_00758b50_wheel_kinematics(
    std::size_t wheel_index,
    const WheelKinematicSlotInput& input) {

    if (wheel_index >= kWheelKinematicsCount) {
        throw std::invalid_argument("FUN_00758b50 wheel index must be in [0, 3]");
    }
    require_finite(input.relative_vector, "FUN_00758b50 relative vector");
    require_finite_value(input.reference_length, "FUN_00758b50 reference length");
    require_finite_value(input.projection_input, "FUN_00758b50 projection input");

    const double length_squared =
        input.relative_vector[0] * input.relative_vector[0] +
        input.relative_vector[1] * input.relative_vector[1] +
        input.relative_vector[2] * input.relative_vector[2];
    require_finite_value(length_squared, "FUN_00758b50 relative length squared");
    const double relative_length = std::sqrt(length_squared);
    require_finite_value(relative_length, "FUN_00758b50 relative length");
    if (relative_length == 0.0) {
        throw std::invalid_argument(
            "FUN_00758b50 normalizes a zero-length relative vector");
    }

    const double inverse_length = 1.0 / relative_length;
    WheelKinematicsVector3d relative_unit = {
        input.relative_vector[0] * inverse_length,
        input.relative_vector[1] * inverse_length,
        input.relative_vector[2] * inverse_length,
    };
    require_finite(relative_unit, "FUN_00758b50 normalized relative vector");

    WheelKinematicObservation result{};
    result.wheel_index = wheel_index;
    result.wheel_state_offset =
        kWheelKinematicsStateBase + wheel_index * kWheelKinematicsStateStride;
    result.wheel_runtime_offset =
        kWheelKinematicsRuntimeBase + wheel_index * kWheelKinematicsRuntimeStride;
    result.relative_vector = input.relative_vector;
    result.relative_length = relative_length;
    result.relative_unit = relative_unit;
    result.reference_length = input.reference_length;
    result.distance_error = input.reference_length - relative_length;
    result.projection_input = input.projection_input;
    result.stored_projection_value = -input.projection_input;
    require_finite_value(result.distance_error, "FUN_00758b50 distance error");
    require_finite_value(
        result.stored_projection_value,
        "FUN_00758b50 stored projection");
    return result;
}

WheelKinematicsBatchResult execute_fun_00758b50_prehelper_batch(
    const std::array<WheelKinematicSlotInput, kWheelKinematicsCount>& inputs) {

    WheelKinematicsBatchResult result{};
    for (std::size_t wheel = 0; wheel < kWheelKinematicsCount; ++wheel) {
        if (inputs[wheel].skip_flag_nonzero) {
            continue;
        }
        result.observations[wheel] =
            prepare_fun_00758b50_wheel_kinematics(wheel, inputs[wheel]);
        result.processed[wheel] = true;
        ++result.processed_count;
    }
    return result;
}

WheelKinematicsPairResult apply_fun_00758b50_pair_delta(
    const WheelKinematicsPairInput& input) {

    require_finite_value(input.source_a_left, "FUN_00758b50 pair source A left");
    require_finite_value(input.source_b_left, "FUN_00758b50 pair source B left");
    require_finite_value(input.source_a_right, "FUN_00758b50 pair source A right");
    require_finite_value(input.source_b_right, "FUN_00758b50 pair source B right");
    require_finite_value(input.scale, "FUN_00758b50 pair scale");
    require_finite_value(
        input.left_destination_before,
        "FUN_00758b50 pair left destination");
    require_finite_value(
        input.right_destination_before,
        "FUN_00758b50 pair right destination");

    WheelKinematicsPairResult result{};
    result.delta =
        ((input.source_a_left - input.source_b_left) -
         (input.source_a_right - input.source_b_right)) *
        input.scale;
    result.left_destination_after =
        input.left_destination_before + result.delta;
    result.right_destination_after =
        input.right_destination_before - result.delta;
    require_finite_value(result.delta, "FUN_00758b50 pair delta");
    require_finite_value(
        result.left_destination_after,
        "FUN_00758b50 pair left result");
    require_finite_value(
        result.right_destination_after,
        "FUN_00758b50 pair right result");
    return result;
}

bool fun_00758b50_final_transform_eligible(
    bool input_pointer_present,
    bool block_flag_0x11c_nonzero) {

    return input_pointer_present && !block_flag_0x11c_nonzero;
}

}  // namespace shift::runtime::physics

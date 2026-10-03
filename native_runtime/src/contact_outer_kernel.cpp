#include "shift_contact_outer_kernel.hpp"

#include <algorithm>
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
        throw std::invalid_argument(
            std::string(label) + " must be finite");
    }
}

double planar_length_xz(const ContactOuterVector3d& vector) {
    const double length = std::sqrt(
        vector[0] * vector[0] + vector[2] * vector[2]);
    require_finite_value(length, "FUN_007675f0 planar distance");
    return length;
}

ContactOuterVector3d normalize_planar_xz(
    const ContactOuterVector3d& vector,
    double length) {

    if (length == 0.0) {
        throw std::invalid_argument(
            "FUN_007675f0 cannot normalize a zero X/Z delta");
    }
    const double inverse = 1.0 / length;
    ContactOuterVector3d result = {
        vector[0] * inverse,
        0.0,
        vector[2] * inverse,
    };
    require_finite(result, "FUN_007675f0 planar direction");
    return result;
}

double clamp_01(double value) {
    return std::min(1.0, std::max(0.0, value));
}

}  // namespace

double execute_fun_00783a30_distance_filter(
    double previous,
    double distance,
    double cap,
    double response) {

    require_finite_value(previous, "FUN_00783a30 previous");
    require_finite_value(distance, "FUN_00783a30 distance");
    require_finite_value(cap, "FUN_00783a30 cap");
    require_finite_value(response, "FUN_00783a30 response");

    const double denominator = cap + response;
    if (denominator == 0.0) {
        throw std::invalid_argument(
            "FUN_00783a30 cap + response must be non-zero");
    }

    const double result =
        (distance - previous) * (response / denominator) + previous;
    require_finite_value(result, "FUN_00783a30 result");
    return result;
}

ContactOuterKernelResult execute_fun_007675f0_outer_arithmetic(
    const ContactOuterKernelInput& input) {

    require_finite(input.planar_delta, "FUN_007675f0 planar delta");
    require_finite_value(
        input.previous_distance_state,
        "FUN_007675f0 previous distance state");
    require_finite_value(
        input.distance_filter_cap,
        "FUN_007675f0 distance filter cap");
    require_finite_value(input.speed_x, "FUN_007675f0 speed X");
    require_finite_value(input.speed_z, "FUN_007675f0 speed Z");
    require_finite_value(input.surface_scalar, "FUN_007675f0 surface scalar");
    require_finite_value(input.base_scalar, "FUN_007675f0 base scalar");
    require_finite_value(
        input.projected_scalar,
        "FUN_007675f0 projected scalar");
    require_finite_value(
        input.alignment_scalar,
        "FUN_007675f0 alignment scalar");
    require_finite_value(input.param_3, "FUN_007675f0 param_3");

    ContactOuterKernelResult result{};
    result.distance = planar_length_xz(input.planar_delta);
    result.planar_direction =
        normalize_planar_xz(input.planar_delta, result.distance);

    if (result.distance <= kContactDistanceLimit) {
        result.filtered_distance_state =
            execute_fun_00783a30_distance_filter(
                input.previous_distance_state,
                result.distance,
                input.distance_filter_cap,
                kContactDistanceFilterResponse);
    } else {
        result.filtered_distance_state = kContactDistanceLimit;
    }

    result.speed = std::sqrt(
        input.speed_x * input.speed_x +
        input.speed_z * input.speed_z);
    require_finite_value(result.speed, "FUN_007675f0 speed");
    result.speed_factor = clamp_01(
        (result.speed - kContactSpeedFactorOffset) /
        kContactSpeedFactorScale);

    result.gate_open =
        result.distance < kContactDistanceLimit &&
        result.distance > kContactDistanceGateMinimum &&
        result.speed > kContactSpeedGateMinimum;

    result.gap =
        result.distance - (input.surface_scalar - kContactGapOffset);
    if (result.gap <= 0.0) {
        result.gap_shape = 0.0;
    } else if (result.gap >= kContactGapScale) {
        result.gap_shape = 1.0;
    } else {
        result.gap_shape = result.gap / kContactGapScale;
    }

    result.force_scalar =
        (input.base_scalar * kContactForceMultiplier -
         input.projected_scalar) *
        (2.0 - result.gap_shape) *
        result.gap_shape *
        input.alignment_scalar *
        result.speed_factor;
    require_finite_value(result.force_scalar, "FUN_007675f0 force scalar");

    result.first_submission_scale =
        result.force_scalar * input.param_3;
    result.second_submission_scale =
        result.first_submission_scale * kContactNegativeSubmissionScale;
    require_finite_value(
        result.first_submission_scale,
        "FUN_007675f0 first submission scale");
    require_finite_value(
        result.second_submission_scale,
        "FUN_007675f0 second submission scale");

    return result;
}

}  // namespace shift::runtime::physics

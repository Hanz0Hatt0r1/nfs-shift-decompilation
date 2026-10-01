#include "shift_hinge_projection.hpp"

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

std::array<double, 3> transform_fun_007aefb0(
    const std::array<float, 9>& matrix,
    const std::array<double, 3>& vector) {

    const float x = static_cast<float>(vector[0]);
    const float y = static_cast<float>(vector[1]);
    const float z = static_cast<float>(vector[2]);
    return {
        static_cast<double>(
            matrix[2] * z +
            matrix[0] * x +
            matrix[1] * y),
        static_cast<double>(
            matrix[5] * z +
            matrix[4] * y +
            matrix[3] * x),
        static_cast<double>(
            matrix[8] * z +
            matrix[7] * y +
            matrix[6] * x),
    };
}

std::array<double, 3> cross_fun_007b1320(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right) {

    return {
        right[2] * left[1] -
            right[1] * left[2],
        right[0] * left[2] -
            left[0] * right[2],
        left[0] * right[1] -
            right[0] * left[1],
    };
}

}  // namespace

HingeProjectionResult evaluate_fun_007bae40_hinge(
    const HingeProjectionInput& input) {

    require_finite(input.body_axis, "HINGE body axis");
    require_finite(input.residual_vector, "HINGE residual vector");
    require_finite(input.sample_angular, "HINGE sample angular");
    require_finite(input.sample_linear, "HINGE sample linear");
    require_finite(input.sample_position, "HINGE sample position");
    require_finite(
        input.sample_frame_offset,
        "HINGE sample frame offset");
    require_finite(input.body_frame, "HINGE body frame");
    if (!std::isfinite(input.linear_scale) ||
        !std::isfinite(input.quadratic_scale)) {
        throw std::invalid_argument(
            "HINGE projection scales must be finite");
    }

    const double ax = input.body_axis[0];
    const double ay = input.body_axis[1];
    const double az = input.body_axis[2];
    const double rx = input.residual_vector[0];
    const double ry = input.residual_vector[1];
    const double rz = input.residual_vector[2];
    const double a0 = input.sample_angular[0];
    const double a1 = input.sample_angular[1];
    const double a2 = input.sample_angular[2];
    const double b0 = input.sample_linear[0];
    const double b1 = input.sample_linear[1];
    const double b2 = input.sample_linear[2];

    const double tx =
        input.linear_scale * ax + rx;
    const double ty =
        input.linear_scale * ay + ry;
    const double tz =
        input.linear_scale * az + rz;

    HingeProjectionResult result{};
    result.coupling_scalar =
        (a0 * b1 - a1 * b0) * az +
        ay * (a2 * b0 - a0 * b2) +
        ax * (a1 * b2 - a2 * b1);
    result.axis_angular =
        az * a2 + ax * a0 + ay * a1;
    result.axis_linear =
        az * b2 + ax * b0 + ay * b1;

    double qx = tx;
    double qy = ty;
    double qz = tz;
    if (input.side_flag != 0u) {
        result.frame_correction_applied = true;
        result.transformed_sample_position =
            transform_fun_007aefb0(
                input.body_frame,
                input.sample_position);
        result.cross_vector =
            cross_fun_007b1320(
                input.sample_frame_offset,
                result.transformed_sample_position);
        qx += input.quadratic_scale *
            result.cross_vector[0];
        qy += input.quadratic_scale *
            result.cross_vector[1];
        qz += input.quadratic_scale *
            result.cross_vector[2];
    }

    const double lane0 =
        a2 * qz +
        a0 * qx +
        a1 * qy -
        result.axis_linear *
            result.coupling_scalar;
    const double lane1 =
        qz * b2 +
        qy * b1 +
        b0 * qx +
        result.axis_angular *
            result.coupling_scalar;

    result.raw_lanes = {lane0, lane1};
    result.sign =
        input.side_flag == 0u ? 1.0 : -1.0;
    result.signed_lanes = {
        result.sign * lane0,
        result.sign * lane1,
    };

    require_finite(result.raw_lanes, "FUN_007bae40 raw lanes");
    require_finite(
        result.signed_lanes,
        "FUN_007bae40 signed lanes");
    require_finite(
        result.transformed_sample_position,
        "FUN_007bae40 transformed sample position");
    require_finite(
        result.cross_vector,
        "FUN_007bae40 cross vector");
    return result;
}

std::vector<double> apply_fun_007bae40_hinge(
    const std::vector<double>& solver_vector,
    std::size_t scalar_base,
    const std::array<double, 2>& signed_lanes) {

    require_finite(solver_vector, "HINGE solver vector");
    require_finite(signed_lanes, "HINGE signed lanes");
    if (scalar_base > solver_vector.size() ||
        solver_vector.size() - scalar_base <
            signed_lanes.size()) {
        throw std::out_of_range(
            "HINGE scalar base is outside solver vector");
    }

    std::vector<double> result = solver_vector;
    result[scalar_base] += signed_lanes[0];
    result[scalar_base + 1u] += signed_lanes[1];
    return result;
}

}  // namespace shift::runtime::physics

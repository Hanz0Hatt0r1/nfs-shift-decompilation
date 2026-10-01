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
        static_cast<double>(matrix[2] * z + matrix[0] * x + matrix[1] * y),
        static_cast<double>(matrix[5] * z + matrix[4] * y + matrix[3] * x),
        static_cast<double>(matrix[8] * z + matrix[7] * y + matrix[6] * x),
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
    require_finite(input.sample_frame_offset, "HINGE sample frame offset");
    if (input.body_frame.has_value()) {
        require_finite(*input.body_frame, "HINGE body frame");
    }
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

    HingeProjectionResult result{};
    result.base_vector = {
        ax * input.linear_scale + rx,
        ay * input.linear_scale + ry,
        az * input.linear_scale + rz,
    };
    result.coupling_scalar =
        (a0 * b1 - a1 * b0) * az +
        ay * (a2 * b0 - a0 * b2) +
        ax * (a1 * b2 - a2 * b1);
    result.axis_angular = ax * a0 + ay * a1 + az * a2;
    result.axis_linear = ax * b0 + ay * b1 + az * b2;
    result.projected_vector = result.base_vector;

    if (input.side_flag != 0u) {
        if (!input.body_frame.has_value()) {
            throw std::invalid_argument(
                "HINGE body frame is required for a nonzero side flag");
        }
        const auto transformed = transform_fun_007aefb0(
            *input.body_frame,
            input.sample_position);
        const double ox = input.sample_frame_offset[0];
        const double oy = input.sample_frame_offset[1];
        const double oz = input.sample_frame_offset[2];
        const std::array<double, 3> cross = {
            transformed[2] * oy - transformed[1] * oz,
            transformed[0] * oz - transformed[2] * ox,
            ox * transformed[1] - transformed[0] * oy,
        };
        result.transformed_sample_position = transformed;
        result.cross_vector = cross;
        for (std::size_t lane = 0; lane < cross.size(); ++lane) {
            result.projected_vector[lane] +=
                input.quadratic_scale * cross[lane];
        }
    }

    const double qx = result.projected_vector[0];
    const double qy = result.projected_vector[1];
    const double qz = result.projected_vector[2];
    result.raw_lanes = {
        a0 * qx + a1 * qy + a2 * qz -
            result.axis_linear * result.coupling_scalar,
        qz * b2 + qy * b1 + b0 * qx +
            result.axis_angular * result.coupling_scalar,
    };
    result.sign = input.side_flag == 0u ? 1.0 : -1.0;
    result.signed_lanes = {
        result.sign * result.raw_lanes[0],
        result.sign * result.raw_lanes[1],
    };

    require_finite(result.base_vector, "FUN_007bae40 base vector");
    require_finite(result.projected_vector, "FUN_007bae40 projected vector");
    require_finite(result.raw_lanes, "FUN_007bae40 raw lanes");
    require_finite(result.signed_lanes, "FUN_007bae40 signed lanes");
    return result;
}

std::vector<double> apply_fun_007bae40_hinge(
    const std::vector<double>& solver_vector,
    std::size_t scalar_base,
    const std::array<double, 2>& signed_lanes) {

    require_finite(solver_vector, "HINGE solver vector");
    require_finite(signed_lanes, "HINGE signed lanes");
    if (scalar_base > solver_vector.size() ||
        solver_vector.size() - scalar_base < signed_lanes.size()) {
        throw std::out_of_range(
            "HINGE scalar base is outside solver vector");
    }

    std::vector<double> result = solver_vector;
    for (std::size_t lane = 0;
         lane < signed_lanes.size();
         ++lane) {
        result[scalar_base + lane] += signed_lanes[lane];
    }
    return result;
}

}  // namespace shift::runtime::physics

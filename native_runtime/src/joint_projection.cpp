#include "shift_joint_projection.hpp"

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

}  // namespace

SdfConstraintScales derive_sdf_constraint_scales(
    std::int32_t system_value) {

    const double base =
        static_cast<double>(system_value) * 0.8;
    return {
        base * base,
        base + base,
    };
}

JointProjectionResult evaluate_fun_007bac60_joint(
    const JointProjectionInput& input) {

    require_finite(input.body_position, "JOINT body position");
    require_finite(input.body_axis, "JOINT body axis");
    require_finite(input.body_correction, "JOINT body correction");
    require_finite(input.sample_position, "JOINT sample position");
    require_finite(input.residual_vector, "JOINT residual vector");
    require_finite(input.scaled_linear, "JOINT scaled linear");
    if (!std::isfinite(input.linear_scale) ||
        !std::isfinite(input.quadratic_scale)) {
        throw std::invalid_argument(
            "JOINT projection scales must be finite");
    }

    const double bx = input.body_position[0];
    const double by = input.body_position[1];
    const double bz = input.body_position[2];
    const double ax = input.body_axis[0];
    const double ay = input.body_axis[1];
    const double az = input.body_axis[2];
    const double cx = input.body_correction[0];
    const double cy = input.body_correction[1];
    const double cz = input.body_correction[2];
    const double sx = input.sample_position[0];
    const double sy = input.sample_position[1];
    const double sz = input.sample_position[2];
    const double rx = input.residual_vector[0];
    const double ry = input.residual_vector[1];
    const double rz = input.residual_vector[2];
    const double lx = input.scaled_linear[0];
    const double ly = input.scaled_linear[1];
    const double lz = input.scaled_linear[2];

    const double d2 = sz * ay - sy * az;
    const double d3 = az * sx - sz * ax;
    const double d5 = sy * ax - ay * sx;

    const double d4 =
        (sx + bx) * input.quadratic_scale +
        (cx + d2) * input.linear_scale +
        (sz * ry - sy * rz) +
        (ay * d5 - az * d3) +
        lx;
    const double d6 =
        (sy + by) * input.quadratic_scale +
        (cy + d3) * input.linear_scale +
        (sx * rz - sz * rx) +
        (az * d2 - ax * d5) +
        ly;
    const double d7 =
        (sz + bz) * input.quadratic_scale +
        (cz + d5) * input.linear_scale +
        (sy * rx - sx * ry) +
        (ax * d3 - ay * d2) +
        lz;

    JointProjectionResult result{};
    result.cross_terms = {d2, d3, d5};
    result.raw_lanes = {d4, d6, d7};
    result.sign = input.side_flag == 0u ? 1.0 : -1.0;
    result.signed_lanes = {
        result.sign * d4,
        result.sign * d6,
        result.sign * d7,
    };
    require_finite(result.raw_lanes, "FUN_007bac60 raw lanes");
    require_finite(result.signed_lanes, "FUN_007bac60 signed lanes");
    return result;
}

std::vector<double> apply_fun_007bac60_joint(
    const std::vector<double>& solver_vector,
    std::size_t scalar_base,
    const std::array<double, 3>& signed_lanes) {

    require_finite(solver_vector, "JOINT solver vector");
    require_finite(signed_lanes, "JOINT signed lanes");
    if (scalar_base > solver_vector.size() ||
        solver_vector.size() - scalar_base < signed_lanes.size()) {
        throw std::out_of_range(
            "JOINT scalar base is outside solver vector");
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

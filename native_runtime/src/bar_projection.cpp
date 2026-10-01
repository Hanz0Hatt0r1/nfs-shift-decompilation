#include "shift_bar_projection.hpp"

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

BarProjectionResult evaluate_fun_007bb090_bar(
    const BarProjectionInput& input) {

    require_finite(input.body_position, "BAR body position");
    require_finite(input.body_axis, "BAR body axis");
    require_finite(input.body_correction, "BAR body correction");
    require_finite(input.sample_position, "BAR sample position");
    require_finite(input.sample_weight, "BAR sample weight");
    require_finite(input.residual_vector, "BAR residual vector");
    require_finite(input.scaled_linear, "BAR scaled linear");
    if (!std::isfinite(input.linear_scale) ||
        !std::isfinite(input.quadratic_scale) ||
        !std::isfinite(input.side_bias)) {
        throw std::invalid_argument(
            "BAR projection scales/bias must be finite");
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
    const double wx = input.sample_weight[0];
    const double wy = input.sample_weight[1];
    const double wz = input.sample_weight[2];
    const double rx = input.residual_vector[0];
    const double ry = input.residual_vector[1];
    const double rz = input.residual_vector[2];
    const double lx = input.scaled_linear[0];
    const double ly = input.scaled_linear[1];
    const double lz = input.scaled_linear[2];

    const double d2 = sz * ay - sy * az;
    const double d3 = az * sx - sz * ax;
    const double d5 = sy * ax - ay * sx;

    BarProjectionResult result{};
    result.cross_terms = {d2, d3, d5};
    result.basis = {
        (sx + bx) * input.quadratic_scale +
            (cx + d2) * input.linear_scale +
            (sz * ry - sy * rz) +
            (ay * d5 - az * d3) +
            lx,
        (sy + by) * input.quadratic_scale +
            (cy + d3) * input.linear_scale +
            (sx * rz - sz * rx) +
            (az * d2 - ax * d5) +
            ly,
        (sz + bz) * input.quadratic_scale +
            (cz + d5) * input.linear_scale +
            (sy * rx - sx * ry) +
            (ax * d3 - ay * d2) +
            lz,
    };

    result.raw_lane =
        wx * result.basis[0] +
        wy * result.basis[1] +
        wz * result.basis[2];

    if (input.side_flag == 0u) {
        result.side_correction = 0.0;
        result.signed_lane = result.raw_lane;
    } else {
        result.side_correction =
            input.side_bias * input.quadratic_scale;
        result.signed_lane =
            -(result.raw_lane - result.side_correction);
    }

    require_finite(result.cross_terms, "FUN_007bb090 cross terms");
    require_finite(result.basis, "FUN_007bb090 basis");
    if (!std::isfinite(result.raw_lane) ||
        !std::isfinite(result.side_correction) ||
        !std::isfinite(result.signed_lane)) {
        throw std::invalid_argument(
            "FUN_007bb090 produced non-finite lane");
    }
    return result;
}

std::vector<double> apply_fun_007bb090_bar(
    const std::vector<double>& solver_vector,
    std::size_t scalar_base,
    double signed_lane) {

    require_finite(solver_vector, "BAR solver vector");
    if (!std::isfinite(signed_lane)) {
        throw std::invalid_argument(
            "BAR signed lane must be finite");
    }
    if (scalar_base >= solver_vector.size()) {
        throw std::out_of_range(
            "BAR scalar base is outside solver vector");
    }

    std::vector<double> result = solver_vector;
    result[scalar_base] += signed_lane;
    return result;
}

}  // namespace shift::runtime::physics

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

struct SdfConstraintScales {
    double quadratic_scale = 0.0;
    double linear_scale = 0.0;
};

SdfConstraintScales derive_sdf_constraint_scales(
    std::int32_t system_value);

struct JointProjectionInput {
    std::array<double, 3> body_position{};
    std::array<double, 3> body_axis{};
    std::array<double, 3> body_correction{};
    std::array<double, 3> sample_position{};
    std::array<double, 3> residual_vector{};
    std::array<double, 3> scaled_linear{};
    double linear_scale = 0.0;
    double quadratic_scale = 0.0;
    std::uint8_t side_flag = 0;
};

struct JointProjectionResult {
    std::array<double, 3> cross_terms{};
    std::array<double, 3> raw_lanes{};
    std::array<double, 3> signed_lanes{};
    double sign = 1.0;
};

JointProjectionResult evaluate_fun_007bac60_joint(
    const JointProjectionInput& input);

std::vector<double> apply_fun_007bac60_joint(
    const std::vector<double>& solver_vector,
    std::size_t scalar_base,
    const std::array<double, 3>& signed_lanes);

}  // namespace shift::runtime::physics

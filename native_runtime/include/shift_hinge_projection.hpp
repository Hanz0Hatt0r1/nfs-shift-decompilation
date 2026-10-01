#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <vector>

namespace shift::runtime::physics {

struct HingeProjectionInput {
    std::array<double, 3> body_axis{};
    std::array<double, 3> residual_vector{};
    std::array<double, 3> sample_angular{};
    std::array<double, 3> sample_linear{};
    std::array<double, 3> sample_position{};
    std::array<double, 3> sample_frame_offset{};
    std::optional<std::array<float, 9>> body_frame;
    double linear_scale = 0.0;
    double quadratic_scale = 0.0;
    std::uint8_t side_flag = 0;
};

struct HingeProjectionResult {
    double coupling_scalar = 0.0;
    double axis_angular = 0.0;
    double axis_linear = 0.0;
    std::array<double, 3> base_vector{};
    std::optional<std::array<double, 3>> transformed_sample_position;
    std::optional<std::array<double, 3>> cross_vector;
    std::array<double, 3> projected_vector{};
    std::array<double, 2> raw_lanes{};
    std::array<double, 2> signed_lanes{};
    double sign = 1.0;
};

HingeProjectionResult evaluate_fun_007bae40_hinge(
    const HingeProjectionInput& input);

std::vector<double> apply_fun_007bae40_hinge(
    const std::vector<double>& solver_vector,
    std::size_t scalar_base,
    const std::array<double, 2>& signed_lanes);

}  // namespace shift::runtime::physics

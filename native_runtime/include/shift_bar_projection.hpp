#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

struct BarProjectionInput {
    std::array<double, 3> body_position{};
    std::array<double, 3> body_axis{};
    std::array<double, 3> body_correction{};
    std::array<double, 3> sample_position{};
    std::array<double, 3> sample_weight{};
    std::array<double, 3> residual_vector{};
    std::array<double, 3> scaled_linear{};
    double linear_scale = 0.0;
    double quadratic_scale = 0.0;
    double side_bias = 0.0;
    std::uint8_t side_flag = 0;
};

struct BarProjectionResult {
    std::array<double, 3> cross_terms{};
    std::array<double, 3> basis{};
    double raw_lane = 0.0;
    double side_correction = 0.0;
    double signed_lane = 0.0;
};

BarProjectionResult evaluate_fun_007bb090_bar(
    const BarProjectionInput& input);

std::vector<double> apply_fun_007bb090_bar(
    const std::vector<double>& solver_vector,
    std::size_t scalar_base,
    double signed_lane);

}  // namespace shift::runtime::physics

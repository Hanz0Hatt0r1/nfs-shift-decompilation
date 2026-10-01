#pragma once

#include <array>
#include <cstddef>
#include <vector>

namespace shift::runtime::physics {

struct BarCrossFrameResult {
    std::array<double, 3> cross{};
    std::array<double, 3> transformed{};
};

struct BarSelfCoefficientResult {
    BarCrossFrameResult frame{};
    std::array<double, 3> inverse_scalar_terms{};
    double coefficient = 0.0;
};

struct BarPairCoefficientResult {
    BarCrossFrameResult outer_frame{};
    std::array<double, 3> inverse_scalar_terms{};
    double raw_coefficient = 0.0;
    double coefficient = 0.0;
    double sign = 1.0;
    std::size_t row = 0;
    std::size_t column = 0;
};

BarCrossFrameResult evaluate_fun_007bb6c0_cross_frame(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& point,
    const std::array<double, 3>& direction);

BarSelfCoefficientResult evaluate_fun_007bb6c0_bar_self(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& point,
    const std::array<double, 3>& direction,
    double inverse_scalar);

BarPairCoefficientResult evaluate_fun_007bb6c0_bar_pair(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& outer_point,
    const std::array<double, 3>& outer_direction,
    const std::array<double, 3>& inner_point,
    const std::array<double, 3>& inner_direction,
    double inverse_scalar,
    std::size_t outer_base,
    std::size_t inner_base,
    bool same_side);

std::vector<double> apply_fun_007bb6c0_bar_scalar(
    const std::vector<double>& matrix,
    std::size_t dimension,
    std::size_t row,
    std::size_t column,
    double value);

}  // namespace shift::runtime::physics

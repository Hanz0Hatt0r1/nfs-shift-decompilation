#pragma once

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace shift::runtime::physics {

struct HingeMatrixRows {
    std::array<double, 3> angular{};
    std::array<double, 3> linear{};
};

struct HingeSelfBlockResult {
    HingeMatrixRows transformed{};
    std::array<double, 3> lower_triangle{};
};

struct HingePairBlockResult {
    HingeMatrixRows transformed_outer{};
    std::array<double, 4> raw_coefficients{};
    std::array<double, 4> block{};
    std::size_t row_base = 0;
    std::size_t column_base = 0;
    double sign = 1.0;
    std::string orientation;
};

HingeMatrixRows transform_fun_007bb250_hinge_rows(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& angular,
    const std::array<double, 3>& linear);

HingeSelfBlockResult evaluate_fun_007bb250_hinge_self(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& angular,
    const std::array<double, 3>& linear);

HingePairBlockResult evaluate_fun_007bb250_hinge_pair(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& outer_angular,
    const std::array<double, 3>& outer_linear,
    const std::array<double, 3>& inner_angular,
    const std::array<double, 3>& inner_linear,
    std::size_t outer_base,
    std::size_t inner_base,
    bool same_side);

std::vector<double> apply_fun_007bb250_hinge_block(
    const std::vector<double>& matrix,
    std::size_t dimension,
    std::size_t row_base,
    std::size_t column_base,
    const std::array<double, 4>& block);

}  // namespace shift::runtime::physics
